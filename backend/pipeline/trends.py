"""Interest score and trends (QT-06: act-3, seq-4, seq-18; UC21/UC22). Plain weighted counts, no model, computed on
request — the volume is tiny; a nightly roll-up can replace the queries later without changing `overview()`.

    score(value)  = views x 1 + saves x 3 + photos sent in a brief x 5     (consented events only; '*:khac' dropped)
    share(value)  = score / sum of scores in its dimension
    trend(value)  = last 7 days vs the average of the 4 weeks before:
                    'dang_tang'  week0 >= 1.5 x avg and >= 5 signals in week0
                    'moi_noi'    no earlier activity and >= 5 signals in week0
                    'dang_giam'  avg >= 5 and week0 <= 0.5 x avg
Only aggregates leave this module: never a session id, account or contact."""

from collections import defaultdict

from psycopg.rows import tuple_row

WEIGHTS = {"xem_khong_gian": 1, "luu_anh": 3, "brief": 5}
RISE, FALL, MIN_SIGNALS, MIN_AVG_FALL = 1.5, 0.5, 5, 5
TOP_PER_DIMENSION, WEEKS_BACK, LEAD_WEEKS = 8, 4, 8
SOURCES = ("form", "chat", "brief", "estimate")
TREND_ORDER = {"dang_tang": 0, "moi_noi": 1, "dang_giam": 2}


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


# brief photos carry no tag snapshot: their space's current tags are used (briefs are rare; noted in the design)
_BRIEF_VALUES = ("FROM bo_suu_tap b JOIN bo_suu_tap_anh a ON a.bo_suu_tap_id = b.id "
                 "JOIN space_gia_tri sg ON sg.space_id = a.space_id JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id "
                 "JOIN chieu_phan_loai d ON d.id = g.chieu_id WHERE b.loai = 'da_gui' ")
_WEEK = "floor(extract(epoch FROM now() - {col}) / 604800)::int"


def overview(conn, days: int) -> dict:
    period = f"{int(days)} days"
    counts = defaultdict(lambda: {"xem": 0, "luu": 0, "brief": 0})
    for value, loai, n in _rows(conn, "SELECT v, loai, count(*) FROM su_kien, unnest(gia_tri) v "
                                      "WHERE created_at > now() - %s::interval GROUP BY v, loai", (period,)):
        counts[value]["xem" if loai == "xem_khong_gian" else "luu"] += n
    for value, n in _rows(conn, "SELECT d.ma_dinh_danh || ':' || g.ma_dinh_danh, count(*) " + _BRIEF_VALUES +
                                "AND b.created_at > now() - %s::interval GROUP BY 1", (period,)):
        counts[value]["brief"] += n

    weekly = defaultdict(lambda: [0] * (WEEKS_BACK + 1))
    signals0 = defaultdict(int)
    for value, loai, w, n in _rows(conn, f"SELECT v, loai, {_WEEK.format(col='created_at')} w, count(*) "
                                         "FROM su_kien, unnest(gia_tri) v WHERE created_at > now() - interval '35 days' "
                                         "GROUP BY 1, 2, 3"):
        if 0 <= w <= WEEKS_BACK:
            weekly[value][w] += n * WEIGHTS[loai]
            signals0[value] += n if w == 0 else 0
    for value, w, n in _rows(conn, f"SELECT d.ma_dinh_danh || ':' || g.ma_dinh_danh, {_WEEK.format(col='b.created_at')}, "
                                   "count(*) " + _BRIEF_VALUES + "AND b.created_at > now() - interval '35 days' GROUP BY 1, 2"):
        if 0 <= w <= WEEKS_BACK:
            weekly[value][w] += n * WEIGHTS["brief"]
            signals0[value] += n if w == 0 else 0
    trends = {v: trend(weekly[v], signals0[v]) for v in weekly}

    dims = _rows(conn, "SELECT id, ma_dinh_danh, ten FROM chieu_phan_loai WHERE hien_thi_cho_khach ORDER BY thu_tu, id")
    names = {f"{d}:{v}": t for d, v, t in _rows(conn, "SELECT d.ma_dinh_danh, g.ma_dinh_danh, g.ten FROM gia_tri_phan_loai g "
                                                     "JOIN chieu_phan_loai d ON d.id = g.chieu_id")}
    chieu, alerts = [], []
    for _, dim, dim_name in dims:
        scores = {v: score(**c) for v, c in counts.items() if v.startswith(dim + ":") and not is_khac(v)}
        pct = shares(scores)
        values = sorted((v for v, s in scores.items() if s > 0), key=lambda v: (-scores[v], v))[:TOP_PER_DIMENSION]
        chieu.append({"ma": dim, "ten": dim_name, "gia_tri": [
            {"ma": v.split(":", 1)[1], "ten": names.get(v, v.split(":", 1)[1]), "diem": scores[v], "ti_le": pct.get(v, 0),
             **counts[v], **trends.get(v, {"thay_doi": None, "xu_huong": None})} for v in values]})
        for v, t in trends.items():
            if v.startswith(dim + ":") and not is_khac(v) and t["xu_huong"]:
                alerts.append({"chieu": dim_name, "ma": v.split(":", 1)[1], "ten": names.get(v, v.split(":", 1)[1]), **t})
    alerts.sort(key=lambda a: (TREND_ORDER[a["xu_huong"]], -(a["thay_doi"] or 0)))

    one = lambda sql, args=(): _rows(conn, sql, args)[0][0] or 0  # noqa: E731
    views = one("SELECT count(*) FROM su_kien WHERE loai = 'xem_khong_gian' AND created_at > now() - %s::interval", (period,))
    anon = dict(_rows(conn, "SELECT loai, sum(so_luong) FROM su_kien_an_danh WHERE ngay > current_date - %s GROUP BY loai",
                      (int(days),)))
    saves = one("SELECT count(*) FROM su_kien WHERE loai = 'luu_anh' AND created_at > now() - %s::interval", (period,))
    leads = dict(_rows(conn, "SELECT nguon, count(*) FROM lead WHERE created_at > now() - %s::interval GROUP BY nguon",
                       (period,)))
    tong = {"luot_xem": views + int(anon.get("xem_khong_gian", 0)), "luot_xem_dong_y": views,
            "ti_le_dong_y": round(100 * views / (views + int(anon.get("xem_khong_gian", 0)))) if views or anon.get("xem_khong_gian") else 0,
            "luot_luu": saves + int(anon.get("luu_anh", 0)),
            "brief": one("SELECT count(*) FROM bo_suu_tap WHERE loai = 'da_gui' AND created_at > now() - %s::interval", (period,)),
            "lead": {s: leads.get(s, 0) for s in SOURCES}}

    by_week = defaultdict(dict)
    for week, nguon, n in _rows(conn, "SELECT date_trunc('week', created_at)::date, nguon, count(*) FROM lead "
                                      "WHERE created_at >= date_trunc('week', now()) - interval '7 weeks' GROUP BY 1, 2"):
        by_week[week][nguon] = n
    weeks = [w for (w,) in _rows(conn, "SELECT generate_series(date_trunc('week', now()) - interval '7 weeks', "
                                       "date_trunc('week', now()), interval '1 week')::date")]
    lead_theo_tuan = [{"tuan_bat_dau": w.isoformat(), **{s: by_week[w].get(s, 0) for s in SOURCES}} for w in weeks]

    top = [{"id": i, "relative_path": p, "space_type": t, "design_style": st, "luot_xem": n} for i, p, t, st, n in _rows(
        conn, "SELECT s.id, s.relative_path, s.space_type, s.design_style, count(*) FROM su_kien e JOIN space s ON s.id = e.space_id "
              "WHERE e.loai = 'xem_khong_gian' AND e.created_at > now() - %s::interval AND s.review_status = 'published' "
              "GROUP BY s.id ORDER BY count(*) DESC, s.id LIMIT 5", (period,))]

    demo = bool(_rows(conn, "SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')")[0][0])
    return {"days": int(days), "tong": tong, "chieu": chieu, "canh_bao": alerts, "lead_theo_tuan": lead_theo_tuan,
            "khong_gian_xem_nhieu": top, "co_du_lieu_mo_phong": demo}
