"""Filter published projects by several dimensions (search-explanations; seq-10 b1-b8, BFD 1.1-1.2).

A project is published when it has at least one published photo. Its values: the labels of its published photos, its
type mapped to 'loai_cong_trinh', its investment level; its area comes from its details. Several values of one
dimension mean any of them; different dimensions all apply. Counts per value use the other dimensions' choices; when
nothing matches, the single filter whose removal gives most projects is suggested. The set is small (tens of
projects), so filtering and counting run in Python over one query.
"""

from collections import defaultdict
from datetime import timedelta

from psycopg.rows import tuple_row

DIMS = ("phong_cach", "loai_cong_trinh", "muc_dau_tu")
TYPE_TO_BUILDING = {"chung-cu": "can_ho", "villa": "biet_thu", "nha-pho": "nha_pho", "van-phong": "van_phong",
                    "fnb": "thuong_mai", "lounge": "thuong_mai", "spa": "thuong_mai", "khach-san": "thuong_mai"}
SORTS = ("moi_nhat", "dien_tich", "xem_nhieu")
NAMES = {"phong_cach": "Phong cách", "loai_cong_trinh": "Loại công trình", "muc_dau_tu": "Mức đầu tư", "dien_tich": "Diện tích"}


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def _projects(conn) -> dict:
    out = {}
    for slug, ten, co_trang, loai, area, muc, first_id, first_path, published, views in _rows(conn, """
        SELECT d.slug, d.ten, d.co_trang, d.loai, d.dien_tich_m2, d.muc_dau_tu,
               (array_agg(s.id ORDER BY s.anh_trang COLLATE "C" NULLS LAST, s.id))[1],
               (array_agg(s.relative_path ORDER BY s.anh_trang COLLATE "C" NULLS LAST, s.id))[1],
               max(s.ngay_xuat_ban),
               COALESCE((SELECT sum(k.so_xem) FROM tk_khong_gian_ngay k JOIN space s2 ON s2.id = k.space_id
                          WHERE s2.du_an_slug = d.slug AND s2.review_status = 'published'
                            AND k.ngay > (SELECT max(ngay) FROM tk_ngay) - 30), 0)
          FROM du_an d JOIN space s ON s.du_an_slug = d.slug AND s.review_status = 'published'
         GROUP BY d.slug"""):
        vals = defaultdict(set)
        if TYPE_TO_BUILDING.get(loai):
            vals["loai_cong_trinh"].add(TYPE_TO_BUILDING[loai])
        if muc:
            vals["muc_dau_tu"].add(muc)
        out[slug] = {"slug": slug, "ten": ten, "co_trang": co_trang, "loai": loai,
                     "dien_tich_m2": float(area) if area is not None else None,
                     "anh_bia": {"id": first_id, "relative_path": first_path},
                     "ngay_xuat_ban": published.isoformat() if published else None, "luot_xem_30": int(views),
                     "_vals": vals}
    for slug, dim, code in _rows(conn, """
        SELECT DISTINCT s.du_an_slug, c.ma_dinh_danh, g.ma_dinh_danh FROM space s
          JOIN space_gia_tri sg ON sg.space_id = s.id JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id
          JOIN chieu_phan_loai c ON c.id = g.chieu_id
         WHERE s.review_status = 'published' AND c.ma_dinh_danh = ANY(%s) AND lower(g.ma_dinh_danh) <> 'khac'""", (list(DIMS),)):
        if slug in out:
            out[slug]["_vals"][dim].add(code)
    return out


def _match(p, sel: dict, area) -> bool:
    for dim, want in sel.items():
        if want and not (p["_vals"][dim] & want):
            return False
    if area and (area[0] is not None or area[1] is not None):
        a = p["dien_tich_m2"]
        if a is None or (area[0] is not None and a < area[0]) or (area[1] is not None and a > area[1]):
            return False
    return True


def filter_projects(conn, sel: dict, area=(None, None), sort="moi_nhat", limit=60) -> dict:
    """sel: {dimension: set of value codes}. area: (from, to) in m2, either None."""
    projects = _projects(conn)
    sel = {d: set(v) for d, v in sel.items() if d in DIMS and v}
    hits = [p for p in projects.values() if _match(p, sel, area)]
    key = {"moi_nhat": lambda p: (p["ngay_xuat_ban"] or "", p["slug"]),
           "dien_tich": lambda p: (p["dien_tich_m2"] if p["dien_tich_m2"] is not None else -1, p["slug"]),
           "xem_nhieu": lambda p: (p["luot_xem_30"], p["slug"])}[sort if sort in SORTS else "moi_nhat"]
    hits.sort(key=key, reverse=True)
    names = {(d, v): t for d, v, t in _rows(conn, "SELECT c.ma_dinh_danh, g.ma_dinh_danh, g.ten FROM gia_tri_phan_loai g "
                                                 "JOIN chieu_phan_loai c ON c.id = g.chieu_id WHERE c.ma_dinh_danh = ANY(%s) "
                                                 "ORDER BY g.id", (list(DIMS),))}
    counts = {}
    for dim in DIMS:  # how many projects each value would give, with the other dimensions' choices
        others = {d: v for d, v in sel.items() if d != dim}
        counts[dim] = {v: sum(1 for p in projects.values() if v in p["_vals"][dim] and _match(p, others, area))
                       for (d, v) in names if d == dim}
    loosen = None
    if not hits and (sel or any(x is not None for x in area)):
        options = [(d, {k: v for k, v in sel.items() if k != d}, area) for d in sel]
        if any(x is not None for x in area):
            options.append(("dien_tich", sel, (None, None)))
        best = max(((d, sum(1 for p in projects.values() if _match(p, s, a))) for d, s, a in options), key=lambda x: x[1])
        if best[1]:
            loosen = {"chieu": best[0], "ten": NAMES[best[0]], "so_du_an": best[1]}
    strip = lambda p: {k: v for k, v in p.items() if k != "_vals"}  # noqa: E731
    return {"tong": len(hits), "du_an": [strip(p) for p in hits[:limit]], "dem": counts,
            "gia_tri": {d: [{"ma": v, "ten": t} for (dd, v), t in names.items() if dd == d] for d in DIMS},
            "noi_long": loosen}
