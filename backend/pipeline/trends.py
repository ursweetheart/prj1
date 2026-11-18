"""Interest score and trends (QT-06: act-3, seq-4, seq-18; UC21/UC22). Plain weighted counts, no model, computed on
request from the analytics store that pipeline/rollup.py fills every night (tracking-pipeline).

    score(value)  = views x 1 + saves x 3 + photos sent in a brief x 5     (consented events only; '*:khac' dropped)
    share(value)  = score / sum of scores in its dimension
    trend(value)  = last 7 days vs the average of the 4 weeks before:
                    'dang_tang'  week0 >= 1.5 x avg and >= 5 signals in week0
                    'moi_noi'    no earlier activity and >= 5 signals in week0
                    'dang_giam'  avg >= 5 and week0 <= 0.5 x avg
Only aggregates leave this module: never a session id, account or contact."""

from collections import defaultdict
from datetime import timedelta

from psycopg.rows import tuple_row

WEIGHTS = {"xem_khong_gian": 1, "luu_anh": 3, "brief": 5}
SCORED = ["xem_khong_gian", "luu_anh"]  # su_kien types in the score; quiz answers (chon_trac_nghiem) are not
RISE, FALL, MIN_SIGNALS, MIN_AVG_FALL = 1.5, 0.5, 5, 5
TOP_PER_DIMENSION, WEEKS_BACK, LEAD_WEEKS = 8, 4, 8
SOURCES = ("form", "chat", "brief", "estimate")
TREND_ORDER = {"dang_tang": 0, "moi_noi": 1, "nhom_moi": 2, "dang_giam": 3}


def is_khac(value: str) -> bool:
    return value.lower().endswith(":khac")


def score(xem=0, luu=0, brief=0) -> int:
    return xem * WEIGHTS["xem_khong_gian"] + luu * WEIGHTS["luu_anh"] + brief * WEIGHTS["brief"]


def shares(scores: dict) -> dict:
    """{value: score} of one dimension -> {value: percent}, 'khac' left out of both sides."""
    kept = {v: s for v, s in scores.items() if not is_khac(v)}
    total = sum(kept.values())
    return {v: round(100 * s / total) for v, s in kept.items()} if total else {}


def trend(weekly: list, signals0: int) -> dict:
    """weekly: [score of the last 7 days, week before, ..., 4 weeks before]; signals0: events in the last 7 days."""
    w0, earlier = weekly[0], weekly[1:WEEKS_BACK + 1]
    avg = sum(earlier) / WEEKS_BACK
    change = round(100 * (w0 - avg) / avg) if avg else None
    if avg == 0:
        label = "moi_noi" if signals0 >= MIN_SIGNALS else None
    elif w0 >= RISE * avg and signals0 >= MIN_SIGNALS:
        label = "dang_tang"
    elif avg >= MIN_AVG_FALL and w0 <= FALL * avg:
        label = "dang_giam"
    else:
        label = None
    return {"thay_doi": change, "xu_huong": label}


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def last_day(conn):
    """The last day in the analytics store (seq-4 b6-b11): every figure here ends with it. None before the first run."""
    return _rows(conn, "SELECT max(ngay) FROM tk_ngay")[0][0]


def _names(conn) -> dict:
    return {f"{d}:{v}": t for d, v, t in _rows(conn, "SELECT d.ma_dinh_danh, g.ma_dinh_danh, g.ten FROM gia_tri_phan_loai g "
                                                     "JOIN chieu_phan_loai d ON d.id = g.chieu_id")}


def taste_groups(conn, end, names=None) -> dict | None:
    """The latest taste-group run up to `end` (act-3), values named; None when no run exists."""
    run = _rows(conn, "SELECT ngay_tinh, so_phien, du_du_lieu FROM tk_nhom_chay WHERE ngay_tinh <= %s ORDER BY ngay_tinh DESC LIMIT 1",
                (end,))
    if not run:
        return None
    day, n, enough = run[0]
    names = names or _names(conn)
    dims = dict(_rows(conn, "SELECT ma_dinh_danh, ten FROM chieu_phan_loai"))
    groups = [{"so_phien": s, "ty_le": round(100 * r), "moi": m,
               "gia_tri": [{"chieu": dims.get(v.split(":", 1)[0], v.split(":", 1)[0]), "ma": v.split(":", 1)[1],
                            "ten": names.get(v, v.split(":", 1)[1])} for v in vals]}
              for s, r, vals, m in _rows(conn, "SELECT so_phien, ty_le, gia_tri, moi FROM tk_nhom_thi_hieu WHERE ngay_tinh = %s "
                                               "ORDER BY nhom", (day,))]
    return {"ngay": day.isoformat(), "so_phien": n, "du_du_lieu": enough, "nhom": groups}


def overview(conn, days: int) -> dict:
    """Read from the analytics store (tracking-pipeline): the period is the `days` days ending with the last processed
    day; scores are summed from the daily aggregates, trends and alerts are the stored ones of that day."""
    demo = bool(_rows(conn, "SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')")[0][0])
    end = last_day(conn)
    dims = _rows(conn, "SELECT id, ma_dinh_danh, ten FROM chieu_phan_loai WHERE hien_thi_cho_khach ORDER BY thu_tu, id")
    if end is None:
        return {"days": int(days), "den_ngay": None, "tong": {"luot_xem": 0, "luot_xem_dong_y": 0, "ti_le_dong_y": 0,
                "luot_luu": 0, "brief": 0, "lead": {s: 0 for s in SOURCES}},
                "chieu": [{"ma": d, "ten": n, "gia_tri": []} for _, d, n in dims], "canh_bao": [], "lead_theo_tuan": [],
                "khong_gian_xem_nhieu": [], "nhom_thi_hieu": None, "co_du_lieu_mo_phong": demo}
    start = end - timedelta(days=int(days) - 1)
    counts = {v: {"xem": int(x), "luu": int(l), "brief": int(b)} for v, x, l, b in _rows(
        conn, "SELECT gia_tri, sum(so_xem), sum(so_luu), sum(so_brief) FROM tk_gia_tri_ngay WHERE ngay BETWEEN %s AND %s "
              "GROUP BY 1", (start, end))}
    trend_of = {v: {"thay_doi": c, "xu_huong": x} for v, c, x in _rows(
        conn, "SELECT gia_tri, thay_doi, xu_huong FROM tk_xu_huong WHERE ngay_tinh = %s", (end,))}
    names = _names(conn)
    chieu, alerts = [], []
    for _, dim, dim_name in dims:
        scores = {v: score(**c) for v, c in counts.items() if v.startswith(dim + ":") and not is_khac(v)}
        pct = shares(scores)
        values = sorted((v for v, s in scores.items() if s > 0), key=lambda v: (-scores[v], v))[:TOP_PER_DIMENSION]
        chieu.append({"ma": dim, "ten": dim_name, "gia_tri": [
            {"ma": v.split(":", 1)[1], "ten": names.get(v, v.split(":", 1)[1]), "diem": scores[v], "ti_le": pct.get(v, 0),
             **counts[v], **trend_of.get(v, {"thay_doi": None, "xu_huong": None})} for v in values]})
        for v, t in trend_of.items():
            if v.startswith(dim + ":") and not is_khac(v) and t["xu_huong"]:
                alerts.append({"chieu": dim_name, "chieu_ma": dim, "ma": v.split(":", 1)[1], "ten": names.get(v, v.split(":", 1)[1]), **t})
    alerts.sort(key=lambda a: (TREND_ORDER[a["xu_huong"]], -(a["thay_doi"] or 0)))
    groups = taste_groups(conn, end, names)
    for g in (groups or {}).get("nhom", []):  # act-3: a new taste group is an alert too
        if g["moi"]:
            alerts.append({"chieu": "Nhóm thị hiếu", "ma": "+".join(v["ma"] for v in g["gia_tri"][:2]),
                           "ten": " · ".join(v["ten"] for v in g["gia_tri"]), "thay_doi": None, "xu_huong": "nhom_moi",
                           "ty_le": g["ty_le"]})

    views, saves = (int(x or 0) for x in _rows(conn, "SELECT sum(so_xem), sum(so_luu) FROM tk_khong_gian_ngay "
                                                      "WHERE ngay BETWEEN %s AND %s", (start, end))[0])
    anon = dict(_rows(conn, "SELECT loai, sum(so_luong) FROM su_kien_an_danh WHERE ngay BETWEEN %s AND %s GROUP BY loai",
                      (start, end)))
    briefs, leads = 0, defaultdict(int)
    for b, ld in _rows(conn, "SELECT so_brief, lead FROM tk_tong_ngay WHERE ngay BETWEEN %s AND %s", (start, end)):
        briefs += b
        for s, n in ld.items():
            leads[s] += n
    anon_views = int(anon.get("xem_khong_gian", 0))
    tong = {"luot_xem": views + anon_views, "luot_xem_dong_y": views,
            "ti_le_dong_y": round(100 * views / (views + anon_views)) if views or anon_views else 0,
            "luot_luu": saves + int(anon.get("luu_anh", 0)), "brief": briefs, "lead": {s: leads.get(s, 0) for s in SOURCES}}

    monday = end - timedelta(days=end.weekday())
    weeks = [monday - timedelta(weeks=i) for i in range(LEAD_WEEKS - 1, -1, -1)]
    by_week = defaultdict(lambda: defaultdict(int))
    for d, ld in _rows(conn, "SELECT ngay, lead FROM tk_tong_ngay WHERE ngay BETWEEN %s AND %s", (weeks[0], end)):
        for s, n in ld.items():
            by_week[d - timedelta(days=d.weekday())][s] += n
    lead_theo_tuan = [{"tuan_bat_dau": w.isoformat(), **{s: by_week[w].get(s, 0) for s in SOURCES}} for w in weeks]

    top = [{"id": i, "relative_path": p, "space_type": t, "design_style": st, "luot_xem": int(n)} for i, p, t, st, n in _rows(
        conn, "SELECT s.id, s.relative_path, s.space_type, s.design_style, sum(k.so_xem) FROM tk_khong_gian_ngay k "
              "JOIN space s ON s.id = k.space_id WHERE k.ngay BETWEEN %s AND %s AND s.review_status = 'published' "
              "GROUP BY s.id HAVING sum(k.so_xem) > 0 ORDER BY sum(k.so_xem) DESC, s.id LIMIT 5", (start, end))]
    return {"days": int(days), "den_ngay": end.isoformat(), "tong": tong, "chieu": chieu, "canh_bao": alerts,
            "lead_theo_tuan": lead_theo_tuan, "khong_gian_xem_nhieu": top, "nhom_thi_hieu": groups,
            "co_du_lieu_mo_phong": demo}
