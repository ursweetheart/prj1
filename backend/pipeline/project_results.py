"""The assistant's examples as projects, ranked by how much of the visitor's request they match
(change: assistant-project-results).

A project is a catalog project (du_an_slug, change project-catalog), else the photo's folder. A constraint counts for a project
when at least one of its candidate photos has it; projects are ordered by constraints matched, then best similarity,
then number of matching photos.
"""

from collections import defaultdict

from pipeline import taxonomy

# request key -> (dimension, how a photo carries it)
FACTORS = {
    "design_style": ("phong_cach", lambda p: [p.get("design_style")]),
    "space_type": ("khong_gian", lambda p: [p.get("space_type")]),
    "project_type": ("loai_cong_trinh", lambda p: p.get("loai_cong_trinh") or []),
}


def folder(relative_path: str) -> str:
    return relative_path.split("/")[0]


def project_key(photo: dict) -> str:
    return photo.get("du_an_slug") or folder(photo["relative_path"])


def _matches(photo: dict, req: dict) -> set:
    return {k for k, (_, values) in FACTORS.items() if req.get(k) and req[k] in values(photo)}


def _named(keys: set, req: dict) -> list[dict]:
    tax = taxonomy.labelled()
    out = []
    for k in FACTORS:  # fixed order: style, room, building type
        if k in keys:
            dim = FACTORS[k][0]
            out.append({"chieu": dim, "ma": req[k],
                        "ten": tax.get(dim, {}).get("values", {}).get(req[k], {}).get("ten", req[k])})
    return out


def rank(photos: list[dict], req: dict, k: int = 3, per: int = 2, keep_order: bool = False) -> list[dict]:
    """photos: candidates {id, relative_path, space_type, design_style, loai_cong_trinh: [codes], sim}, best first.
    -> [{slug, folder, khop: [{chieu, ma, ten}], so_anh_khop, anh: [photo]}], at most k projects of at most `per` photos;
    slug is the project key, folder the best photo's folder (kept for the chat widget until it reads slug).
    keep_order: projects in the order their first photo appears (an answer that cites photos keeps the AI's order)."""
    groups = defaultdict(list)
    for p in photos:
        groups[project_key(p)].append(p)
    projects = []
    for i, (name, ps) in enumerate(groups.items()):  # dicts keep first-appearance order
        matched = set().union(*(_matches(p, req) for p in ps))
        best = sorted(ps, key=lambda p: (-len(_matches(p, req)), -(p.get("sim") or 0)))[:per]
        projects.append({"slug": name, "folder": folder(best[0]["relative_path"]), "khop": _named(matched, req), "so_anh_khop": len(ps), "anh": best,
                         "_key": (i,) if keep_order else (-len(matched), -max(p.get("sim") or 0 for p in ps), -len(ps))})
    projects.sort(key=lambda p: p["_key"])
    for p in projects:
        del p["_key"]
    return projects[:k]


LOAI = ("COALESCE((SELECT array_agg(v.ma_dinh_danh) FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id "
        "JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE sg.space_id = s.id AND d.ma_dinh_danh = 'loai_cong_trinh'), '{}')")


def _row(r) -> dict:
    return {"id": r[0], "relative_path": r[1], "space_type": r[2], "design_style": r[3], "sim": float(r[4]),
            "loai_cong_trinh": list(r[5] or []), "du_an_slug": r[6], "anh_trang": r[7]}


def candidates(text: str, limit: int = 60) -> list[dict]:
    """Published photos closest to the text (SigLIP, as pipeline.search), with their building-type tags. No per-project
    cap and no room filter: how many rooms of a project match is what the ranking is about."""
    import numpy as np
    import psycopg
    from pgvector.psycopg import register_vector

    from pipeline.search import _embedder
    from pipeline.store import DSN

    vec = np.asarray(_embedder().embed_text(text), dtype=np.float32)
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        rows = conn.execute(f"SELECT s.id, s.relative_path, s.space_type, s.design_style, 1 - (s.embedding <=> %s), {LOAI}, "
                            "s.du_an_slug, s.anh_trang "
                            "FROM space s WHERE s.review_status = 'published' AND s.embedding IS NOT NULL "
                            "ORDER BY s.embedding <=> %s LIMIT %s", (vec, vec, limit)).fetchall()
    return [_row(r) for r in rows]


def with_project_types(photos: list[dict]) -> list[dict]:
    """Add loai_cong_trinh tags and the catalog project to photos that came from elsewhere (the photo-description answer)."""
    import psycopg

    from pipeline.store import DSN

    if not photos:
        return photos
    with psycopg.connect(DSN) as conn:
        rows = {r[0]: r[1:] for r in conn.execute(f"SELECT s.id, {LOAI}, s.du_an_slug, s.anh_trang FROM space s "
                                                   "WHERE s.id = ANY(%s)", ([p["id"] for p in photos],)).fetchall()}
    return [{**p, "loai_cong_trinh": list((rows.get(p["id"]) or [None])[0] or []),
             "du_an_slug": (rows.get(p["id"]) or [None, None])[1], "anh_trang": (rows.get(p["id"]) or [None, None, None])[2]}
            for p in photos]


def public(projects: list[dict]) -> list[dict]:
    """What the chat returns: the project's name and whether it has a page; no similarity scores or tag lists."""
    import psycopg

    from pipeline.store import DSN

    keep = ("id", "relative_path", "space_type", "design_style", "anh_trang")
    names = {}
    if projects:
        with psycopg.connect(DSN) as conn:
            names = {r[0]: r[1:] for r in conn.execute("SELECT slug, ten, co_trang FROM du_an WHERE slug = ANY(%s)",
                                                       ([p["slug"] for p in projects],)).fetchall()}
    return [{**p, "ten": names.get(p["slug"], (p["slug"].replace("_", " "),))[0],
             "co_trang": names.get(p["slug"], (None, False))[1],
             "anh": [{k: a.get(k) for k in keep} for a in p["anh"]]} for p in projects]
