"""Project catalog (change: project-catalog). One du_an row per project; a space belongs to one through space.du_an_slug.

    parse_site_projects(text)   src/data/projects.js -> [{slug, ten, loai, nam, mo_ta_ngan, thu_tu}]
    site_photos(root)           {slug: [file, ...]} of src/assets/projects, by file name (the site's order)
    match(site, spaces)         mutual-best pairs at or above THRESHOLD between site-photo and space embeddings
    upsert_site / link / place_leftovers / project_for_folder   the database side of sync_projects.py
"""
import re
from collections import Counter
from pathlib import Path

from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent.parent.parent / "src"   # /src in Docker (read-only mount)
SITE_JS = ROOT / "data" / "projects.js"
SITE_PHOTOS = ROOT / "assets" / "projects"
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
THRESHOLD = 0.95        # same render re-exported: ~0.98+; two rooms of one project rarely pass 0.9
NEAR_MISS = 0.85        # the dry run lists closest non-matches above this, to check THRESHOLD
SITE_FIELDS = ("ten", "loai", "nam", "mo_ta_ngan", "thu_tu")

_BLOCK = re.compile(r"const PROJECTS = \[(.*?)\n\]", re.S)
_ENTRY = re.compile(r"^\s*\{(.*)\},?\s*$")
_PAIR = re.compile(r"(\w+):\s*(?:'((?:[^'\\]|\\.)*)'|(\d+))")


def parse_site_projects(text: str) -> list[dict]:
    """shortcut: single-line object literals only; switch to a JSON export if projects.js grows nested fields.
    Raises ValueError when the list is missing or empty, or a line in it isn't one project, so nothing partial is written."""
    m = _BLOCK.search(text)
    if not m:
        raise ValueError("projects.js: no `const PROJECTS = [ ... ]` block")
    out = []
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("//"):
            continue
        e = _ENTRY.match(line)
        if not e:
            raise ValueError(f"projects.js: can't read line {line.strip()[:80]!r}")
        f = {k: (s.replace("\\'", "'") if n == "" else int(n)) for k, s, n in _PAIR.findall(e.group(1))}
        if not re.fullmatch(r"[a-z0-9-]{1,60}", f.get("slug", "")) or not f.get("name"):
            raise ValueError(f"projects.js: entry without a valid slug and name: {line.strip()[:80]!r}")
        out.append({"slug": f["slug"], "ten": f["name"], "loai": f.get("loai"), "nam": f.get("year"),
                    "mo_ta_ngan": f.get("brief"), "thu_tu": len(out) + 1})
    if not out:
        raise ValueError("projects.js: the project list is empty")
    return out


def site_photos(root: Path = SITE_PHOTOS) -> dict:
    out = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(f.name for f in d.iterdir() if f.suffix.lower() in IMAGE_TYPES)
        if files:
            out[d.name] = files
    return out


def match(site: dict, spaces: dict, threshold: float = THRESHOLD):
    """site {key: unit vector}, spaces {id: unit vector} -> ([(key, id, score)] mutual best >= threshold,
    [(key, id, score)] best pairs below threshold but >= NEAR_MISS, highest first)."""
    import numpy as np

    if not site or not spaces:
        return [], []
    keys, ids = list(site), list(spaces)
    sim = np.asarray([site[k] for k in keys], dtype=float) @ np.asarray([spaces[i] for i in ids], dtype=float).T
    best_space, best_site = sim.argmax(axis=1), sim.argmax(axis=0)
    pairs, near = [], []
    for r, c in enumerate(best_space):
        score = round(float(sim[r, c]), 4)
        if best_site[c] == r and score >= threshold:
            pairs.append((keys[r], ids[c], score))
        elif score >= NEAR_MISS:
            near.append((keys[r], ids[c], score))
    return pairs, sorted(near, key=lambda p: -p[2])


def folder_project_slug(folder: str, taken) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", folder.lower().replace("_", "-")).strip("-")[:50] or "thu-muc"
    return f"{slug}-thu-muc" if slug in taken else slug


def upsert_site(conn, projects: list[dict], with_photos: set) -> int:
    """Site fields only (staff fields are never written here); projects gone from the list lose their page."""
    for p in projects:
        conn.execute(
            "INSERT INTO du_an (slug, ten, loai, nam, mo_ta_ngan, thu_tu, co_trang) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (slug) DO UPDATE SET ten=EXCLUDED.ten, loai=EXCLUDED.loai, nam=EXCLUDED.nam, "
            "mo_ta_ngan=EXCLUDED.mo_ta_ngan, thu_tu=EXCLUDED.thu_tu, co_trang=EXCLUDED.co_trang, cap_nhat_luc=now() "
            "WHERE (du_an.ten, du_an.loai, du_an.nam, du_an.mo_ta_ngan, du_an.thu_tu, du_an.co_trang) IS DISTINCT FROM "
            "(EXCLUDED.ten, EXCLUDED.loai, EXCLUDED.nam, EXCLUDED.mo_ta_ngan, EXCLUDED.thu_tu, EXCLUDED.co_trang)",
            (p["slug"], p["ten"], p["loai"], p["nam"], p["mo_ta_ngan"], p["thu_tu"], p["slug"] in with_photos))
    return conn.execute("UPDATE du_an SET co_trang = false, thu_tu = NULL, cap_nhat_luc = now() "
                        "WHERE thu_tu IS NOT NULL AND NOT slug = ANY(%s)", ([p["slug"] for p in projects],)).rowcount


def link(conn, pairs) -> int:
    """pairs [((slug, file), space_id, score)]: a space already in a project, or a site photo already linked, is left alone."""
    n = 0
    for (slug, file), sid, score in pairs:
        if conn.execute("SELECT 1 FROM space WHERE du_an_slug = %s AND anh_trang = %s", (slug, file)).fetchone():
            continue
        if conn.execute("UPDATE space SET du_an_slug = %s, anh_trang = %s WHERE id = %s AND du_an_slug IS NULL",
                        (slug, file, sid)).rowcount:
            conn.execute("INSERT INTO nhat_ky_du_an (du_an_slug, hanh_dong, chi_tiet) VALUES (%s, 'lien_ket', %s)",
                         (slug, Jsonb({"space_id": sid, "anh_trang": file, "diem": score})))
            n += 1
    return n


def _folder(relative_path: str) -> str:
    return relative_path.split("/", 1)[0]


def project_for_folder(conn, folder: str, dry: bool = False) -> str:
    """The project most of the folder's spaces belong to; else the site project the folder is named after; else the
    folder's own project (created unless dry)."""
    row = conn.execute("SELECT du_an_slug, count(*) FROM space WHERE split_part(relative_path, '/', 1) = %s "
                       "AND du_an_slug IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 1", (folder,)).fetchone()
    if row:
        return row[0]
    site = conn.execute("SELECT slug FROM du_an WHERE slug = %s AND thu_tu IS NOT NULL", (folder.replace("_", "-"),)).fetchone()
    if site:  # the project-space-sync naming: folder = slug with '-' -> '_'
        return site[0]
    taken = {r[0] for r in conn.execute("SELECT slug FROM du_an WHERE thu_tu IS NOT NULL OR co_trang")}
    slug = folder_project_slug(folder, taken)
    if not dry:
        conn.execute("INSERT INTO du_an (slug, ten) VALUES (%s, %s) ON CONFLICT (slug) DO NOTHING", (slug, folder))
    return slug


def place_leftovers(conn, dry: bool = False) -> dict:
    """Spaces in no project join their folder's majority project, or the folder's own project. -> {folder: slug}"""
    rows = conn.execute("SELECT DISTINCT split_part(relative_path, '/', 1) FROM space WHERE du_an_slug IS NULL").fetchall()
    out = {}
    for (folder,) in rows:
        slug = out[folder] = project_for_folder(conn, folder, dry)
        if not dry:
            conn.execute("UPDATE space SET du_an_slug = %s WHERE split_part(relative_path, '/', 1) = %s AND du_an_slug IS NULL",
                         (slug, folder))
    return out


def destinations(conn) -> dict:
    """{folder: Counter(slug)}: where each folder's spaces went (the dry run and the report)."""
    out = {}
    for path, slug in conn.execute("SELECT relative_path, du_an_slug FROM space"):
        out.setdefault(_folder(path), Counter())[slug] += 1
    return out
