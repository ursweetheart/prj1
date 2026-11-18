"""python sync_projects.py [--dry-run] [--ingest [--limit N] [slug ...]]   (change: project-catalog)

1. Adds / updates the site's projects (src/data/projects.js) in du_an: site fields only, staff details untouched.
2. Links each site photo to the stored space showing the same picture (SigLIP2, mutual best, >= THRESHOLD), so
   nothing is analysed twice. Existing links are never overwritten. Every link is logged with its score.
3. Spaces still in no project join their folder's majority project, or the folder's own project (no page).
4. --ingest: up to --limit unmatched site photos become draft spaces of their project (one Gemini call each).

The whole run is one transaction; --dry-run prints the same report and rolls it back.
"""
import argparse
import os
import shutil
import sys

import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from pipeline import projects as pj
from pipeline.store import DSN

IMG_DIR = "image_d3"


def cached_vectors(conn) -> dict:
    """{(slug, file): (mtime, vector)} from earlier runs."""
    rows = conn.execute("SELECT chi_tiet FROM nhat_ky_du_an WHERE hanh_dong = 'nhung' ORDER BY id").fetchall()
    return {(d["slug"], d["file"]): (d["mtime"], d["vec"]) for (d,) in rows}


def embed_site(conn, photos: dict, wanted: list) -> dict:
    """{(slug, file): unit vector} for the wanted site photos; only new or changed files are embedded (CPU)."""
    cache, out, todo = cached_vectors(conn), {}, []
    for key in wanted:
        mtime = os.path.getmtime(pj.SITE_PHOTOS / key[0] / key[1])
        if key in cache and cache[key][0] == mtime:
            out[key] = cache[key][1]
        else:
            todo.append((key, mtime))
    if todo:
        from pipeline.vision_embedder import VisionEmbedder
        emb = VisionEmbedder()
        for i, (key, mtime) in enumerate(todo, 1):
            out[key] = emb.embed_image(pj.SITE_PHOTOS / key[0] / key[1])
            conn.execute("INSERT INTO nhat_ky_du_an (hanh_dong, chi_tiet) VALUES ('nhung', %s)",  # before the project rows
                         (Jsonb({"slug": key[0], "file": key[1], "mtime": mtime, "vec": out[key]}),))
            if i % 50 == 0:
                print(f"  embedded {i}/{len(todo)}", flush=True)
    return out


def run(conn, projects: list, photos: dict, site_vecs: dict, threshold: float = pj.THRESHOLD) -> dict:
    """The database side, with site-photo vectors given (tests pass their own). -> report"""
    pj.upsert_site(conn, projects, set(photos))
    listed = {p["slug"] for p in projects}
    linked = set(conn.execute("SELECT du_an_slug, anh_trang FROM space WHERE anh_trang IS NOT NULL").fetchall())
    site = {k: v for k, v in site_vecs.items() if k[0] in listed and k not in linked}
    spaces = dict(conn.execute("SELECT id, embedding FROM space WHERE du_an_slug IS NULL AND embedding IS NOT NULL").fetchall())
    pairs, near = pj.match(site, {i: v.to_list() if hasattr(v, "to_list") else v for i, v in spaces.items()}, threshold)
    n = pj.link(conn, pairs)
    placed = pj.place_leftovers(conn)
    now_linked = set(conn.execute("SELECT du_an_slug, anh_trang FROM space WHERE anh_trang IS NOT NULL").fetchall())
    unmatched = sorted(k for k in ((s, f) for s, fs in photos.items() if s in listed for f in fs) if k not in now_linked)
    return {"linked": n, "pairs": pairs, "near": near, "placed": placed, "unmatched": unmatched,
            "destinations": pj.destinations(conn)}


def ingest(conn, keys: list) -> int:
    """Unmatched site photos -> draft spaces in <slug with _>/<file> (project-space-sync naming) of their project."""
    from pipeline.processor import SpaceImageProcessor
    from pipeline.store import save_records

    processor = SpaceImageProcessor()
    for i, (slug, file) in enumerate(keys, 1):
        rel = f"{slug.replace('-', '_')}/{file}"
        dest = os.path.join(IMG_DIR, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(pj.SITE_PHOTOS / slug / file, dest)
        save_records([processor.process_image(dest, base_dir=IMG_DIR)])  # its own connection: committed per photo
        conn.execute("UPDATE space SET du_an_slug = %s, anh_trang = %s WHERE relative_path = %s", (slug, file, rel))
        conn.commit()
        print(f"[{i}/{len(keys)}] {rel}", flush=True)
    return len(keys)


def report(r: dict) -> None:
    per = {}
    for (slug, _), _, _ in r["pairs"]:
        per[slug] = per.get(slug, 0) + 1
    miss = {}
    for slug, _ in r["unmatched"]:
        miss[slug] = miss.get(slug, 0) + 1
    print(f"linked {r['linked']} site photo(s) to stored spaces; {len(r['unmatched'])} site photo(s) unmatched")
    for slug in sorted(set(per) | set(miss)):
        if per.get(slug):
            print(f"  {slug}: {per[slug]} matched, {miss.get(slug, 0)} unmatched")
    print(f"projects with no stored photo yet: {sum(1 for s in miss if not per.get(s))}")
    print("where each folder's spaces are:")
    for folder, c in sorted(r["destinations"].items()):
        print(f"  {folder}: " + ", ".join(f"{s} ({n})" for s, n in c.most_common()))
    if r["near"]:
        print(f"closest non-matches (>= {pj.NEAR_MISS}):")
        for (slug, file), sid, score in r["near"][:10]:
            print(f"  {slug}/{file} ~ space {sid}: {score}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("slugs", nargs="*", help="with --ingest: only these projects")
    args = ap.parse_args()

    projects = pj.parse_site_projects(pj.SITE_JS.read_text(encoding="utf-8"))
    photos = pj.site_photos()
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        wanted = [(s, f) for s, fs in photos.items() for f in fs]
        r = run(conn, projects, photos, embed_site(conn, photos, wanted))
        report(r)
        if args.dry_run:
            conn.rollback()
            print("dry run: nothing written")
            return
        conn.commit()
        if args.ingest:
            todo = [k for k in r["unmatched"] if not args.slugs or k[0] in args.slugs]
            print(f"ingested {ingest(conn, todo[:args.limit])} photo(s)")


if __name__ == "__main__":
    main()
