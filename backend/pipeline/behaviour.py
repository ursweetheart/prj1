"""Behaviour on the site (UC21; class-4 SuKien; roadmap 3.1; change behaviour-events). Aggregates of the consented
behaviour events, with the anonymous daily counts beside them. Only counts and averages leave this module."""

from psycopg.rows import tuple_row

TYPES = ("xem_trang", "xem_du_an", "bam_CTA", "gui_form", "nhan_chatbot", "chia_se", "ap_dung_bo_loc")
TOP = 10


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def overview(conn, days: int) -> dict:
    period = f"{int(days)} days"
    win = "created_at > now() - %s::interval"

    pages = [{"trang": t, "luot_xem": n, "giay_tb": round(ms / 1000) if ms is not None else None,
              "cuon_tb": round(100 * sc) if sc is not None else None}
             for t, n, ms, sc in _rows(conn, f"""
        SELECT trang, count(*), avg(thoi_gian_dung_ms), avg(do_sau_cuon) FROM su_kien
         WHERE loai IN ('xem_trang', 'xem_du_an') AND trang IS NOT NULL AND {win}
         GROUP BY trang ORDER BY count(*) DESC, trang LIMIT %s""", (period, TOP))]

    projects = [{"du_an": d, "luot_xem": n, "giay_tb": round(ms / 1000) if ms is not None else None}
                for d, n, ms in _rows(conn, f"""
        SELECT doi_tuong, count(*), avg(thoi_gian_dung_ms) FROM su_kien
         WHERE loai = 'xem_du_an' AND doi_tuong IS NOT NULL AND {win}
         GROUP BY doi_tuong ORDER BY count(*) DESC, doi_tuong LIMIT %s""", (period, TOP))]

    cta = {}
    for target, page, n in _rows(conn, f"SELECT doi_tuong, coalesce(trang, '?'), count(*) FROM su_kien "
                                       f"WHERE loai = 'bam_CTA' AND {win} GROUP BY 1, 2", (period,)):
        c = cta.setdefault(target, {"dich": target, "so_lan": 0, "tu_trang": []})
        c["so_lan"] += n
        c["tu_trang"].append({"trang": page, "so_lan": n})
    for c in cta.values():
        c["tu_trang"].sort(key=lambda x: (-x["so_lan"], x["trang"]))

    count_by = lambda loai: dict(_rows(conn, f"SELECT doi_tuong, count(*) FROM su_kien WHERE loai = %s AND {win} "  # noqa: E731
                                             "GROUP BY 1", (loai, period)))
    totals = dict(_rows(conn, f"SELECT loai, count(*) FROM su_kien WHERE loai = ANY(%s) AND {win} GROUP BY 1",
                        (list(TYPES), period)))
    anon = {k: int(v) for k, v in _rows(conn, "SELECT loai, sum(so_luong) FROM su_kien_an_danh "
                                              "WHERE ngay > current_date - %s AND loai = ANY(%s) GROUP BY loai",
                                        (int(days), list(TYPES)))}
    filters = [{"gia_tri": v, "so_lan": n} for v, n in _rows(conn, f"""
        SELECT v, count(*) FROM su_kien, unnest(gia_tri) v WHERE loai = 'ap_dung_bo_loc' AND {win}
         GROUP BY v ORDER BY count(*) DESC, v LIMIT %s""", (period, TOP))]
    demo = bool(_rows(conn, "SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')")[0][0])
    return {"days": int(days), "trang": pages, "du_an": projects,
            "cta": sorted(cta.values(), key=lambda c: (-c["so_lan"], c["dich"])),
            "form": count_by("gui_form"), "chia_se": count_by("chia_se"), "bo_loc": filters,
            "dong_y": {t: totals.get(t, 0) for t in TYPES}, "an_danh": {t: anon.get(t, 0) for t in TYPES},
            "co_du_lieu_mo_phong": demo}
