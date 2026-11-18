"""Behaviour on the site (UC21; class-4 SuKien; roadmap 3.1; change behaviour-events). Read from the analytics store
(tracking-pipeline: tk_hanh_vi_ngay, filled every night), with the anonymous daily counts beside the consented ones.
Only counts and averages leave this module."""

from collections import defaultdict
from datetime import timedelta

from psycopg.rows import tuple_row

from pipeline.trends import last_day

TYPES = ("xem_trang", "xem_du_an", "bam_CTA", "gui_form", "nhan_chatbot", "chia_se", "ap_dung_bo_loc",
         "tim_kiem", "xem_goi_y_tuong_tu", "chon_goi_y",
         "phong_to_anh", "chuyen_anh", "bam_hotspot")  # the last three: visitor-services-hotspots (Tùng)
TOP = 10


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def overview(conn, days: int) -> dict:
    demo = bool(_rows(conn, "SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')")[0][0])
    end = last_day(conn)
    if end is None:
        return {"days": int(days), "den_ngay": None, "trang": [], "du_an": [], "cta": [], "form": {}, "chia_se": {}, "bo_loc": [],
                "tim_kiem": {}, "goi_y": {"hien": 0, "chon": 0, "ty_le": None}, "hotspot": [],
                "dong_y": {t: 0 for t in TYPES}, "an_danh": {t: 0 for t in TYPES}, "co_du_lieu_mo_phong": demo}
    start = end - timedelta(days=int(days) - 1)
    rows = _rows(conn, "SELECT loai, trang, doi_tuong, sum(so_luot), sum(tong_dung_ms), sum(so_co_dung), sum(tong_cuon), "
                       "sum(so_co_cuon) FROM tk_hanh_vi_ngay WHERE ngay BETWEEN %s AND %s GROUP BY 1, 2, 3", (start, end))

    def agg(key, kinds):
        out = defaultdict(lambda: [0, 0, 0, 0.0, 0])
        for loai, trang, obj, n, ms, n_ms, sc, n_sc in rows:
            if loai in kinds:
                a = out[key(trang, obj)]
                a[0] += n; a[1] += ms; a[2] += n_ms; a[3] += sc; a[4] += n_sc  # noqa: E702
        return out

    pages = [{"trang": t, "luot_xem": a[0], "giay_tb": round(a[1] / a[2] / 1000) if a[2] else None,
              "cuon_tb": round(100 * a[3] / a[4]) if a[4] else None}
             for t, a in sorted(agg(lambda tr, o: tr, ("xem_trang", "xem_du_an")).items(), key=lambda x: (-x[1][0], x[0]))
             if t][:TOP]
    projects = [{"du_an": d, "luot_xem": a[0], "giay_tb": round(a[1] / a[2] / 1000) if a[2] else None}
                for d, a in sorted(agg(lambda tr, o: o, ("xem_du_an",)).items(), key=lambda x: (-x[1][0], x[0])) if d][:TOP]
    cta = {}
    for loai, trang, target, n, *_ in rows:
        if loai == "bam_CTA":
            c = cta.setdefault(target, {"dich": target, "so_lan": 0, "tu_trang": []})
            c["so_lan"] += n
            c["tu_trang"].append({"trang": trang or "?", "so_lan": n})
    for c in cta.values():
        c["tu_trang"].sort(key=lambda x: (-x["so_lan"], x["trang"]))
    def count_by(loai):
        return {obj: a[0] for obj, a in agg(lambda tr, o: o, (loai,)).items()}

    totals = defaultdict(int)
    for loai, _trang, _obj, n, *_ in rows:
        totals[loai] += n
    anon = {k: int(v) for k, v in _rows(conn, "SELECT loai, sum(so_luong) FROM su_kien_an_danh WHERE ngay BETWEEN %s AND %s "
                                              "AND loai = ANY(%s) GROUP BY loai", (start, end, list(TYPES)))}
    filters = sorted(({"gia_tri": v, "so_lan": n} for v, n in count_by("ap_dung_bo_loc").items() if v),
                     key=lambda f: (-f["so_lan"], f["gia_tri"]))[:TOP]
    # visitor-services-hotspots (Tùng): most opened hotspots, "<space id>/mon_do_<item id>" or "<space id>/<label slug>"
    hotspots = sorted(({"doi_tuong": d, "so_lan": n} for d, n in count_by("bam_hotspot").items() if d),
                      key=lambda h: (-h["so_lan"], h["doi_tuong"]))[:TOP]
    shown, chosen = totals["xem_goi_y_tuong_tu"], totals["chon_goi_y"]
    return {"days": int(days), "den_ngay": end.isoformat(), "trang": pages, "du_an": projects,
            "cta": sorted(cta.values(), key=lambda c: (-c["so_lan"], c["dich"])),
            "form": count_by("gui_form"), "chia_se": count_by("chia_se"), "bo_loc": filters, "hotspot": hotspots,
            "tim_kiem": count_by("tim_kiem"),
            "goi_y": {"hien": shown, "chon": chosen, "ty_le": round(100 * chosen / shown) if shown else None},
            "dong_y": {t: totals.get(t, 0) for t in TYPES}, "an_danh": {t: anon.get(t, 0) for t in TYPES},
            "co_du_lieu_mo_phong": demo}
