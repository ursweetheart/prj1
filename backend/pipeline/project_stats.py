"""Per-project results (BFD 5.4; act-1 "theo dõi hiệu quả sau 30 ngày"; roadmap 3.5). Computed on request, like
trends.overview — a handful of grouped queries over tens of rows.

A project is a photo folder: the first segment of space.relative_path (as on the review screen).

    views / saves  consented su_kien 'xem_khong_gian' / 'luu_anh' on the folder's published photos, in the period
    leads          distinct leads in the period whose ngu_canh names the folder's page (du_an, '-' -> '_'), whose
                   ngu_canh names one of its photos (space_id), or whose brief sent one of its photos
    published      earliest review_log 'advance' to 'published' of the folder; else its earliest 'ingest' (approximate)
    status         age >= REVIEW_DAYS ("eligible"): 'can_xem_lai' when views in the last VIEW_WINDOW days
                   < LOW x the median of the eligible projects (needs >= MIN_COMPARE eligible), else 'on';
                   younger: 'dang_theo_doi' with the days left. The status never depends on the period shown.
Only counts leave this module: never a session id, account or contact."""

import os
from statistics import median

from psycopg.rows import tuple_row

WINDOW = 30          # days after publishing before a project is judged, and the view window it is judged on
LOW = 0.5            # below LOW x the median of eligible projects -> 'can_xem_lai'
MIN_COMPARE = 3      # fewer eligible projects than this -> nobody is flagged
FEW_PHOTOS = 0.5     # 'it_anh': published photos < FEW_PHOTOS x the median photos per project
SHORT_CAPTION = 0.5  # 'mo_ta_ngan': caption length < SHORT_CAPTION x the folder's median caption length
LOW_CONFIDENCE = 0.5
TAG_DIMS = {"loai_cong_trinh": "thieu_loai_cong_trinh", "muc_dau_tu": "thieu_muc_dau_tu"}
FOLDER = "split_part(s.relative_path, '/', 1)"


def review_days() -> int:
    """Age at which a project is judged. D3_PROJECT_REVIEW_DAYS overrides it for a demo (e.g. 0)."""
    try:
        return max(0, int(os.environ.get("D3_PROJECT_REVIEW_DAYS", WINDOW)))
    except ValueError:
        return WINDOW


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def statuses(projects: list, days_needed: int) -> dict:
    """projects: [{folder, tuoi (days since published or None), luot_xem_cua_so}] -> {folder: (trang_thai, con_ngay)}
    and the comparison used. Pure, so the rule can be tested without the database."""
    eligible = [p for p in projects if p["tuoi"] is not None and p["tuoi"] >= days_needed]
    med = median(p["luot_xem_cua_so"] for p in eligible) if eligible else None
    compare = len(eligible) >= MIN_COMPARE
    out = {}
    for p in projects:
        if p["tuoi"] is None:
            out[p["folder"]] = ("on", None)
        elif p["tuoi"] < days_needed:
            out[p["folder"]] = ("dang_theo_doi", days_needed - p["tuoi"])
        elif compare and p["luot_xem_cua_so"] < LOW * med:
            out[p["folder"]] = ("can_xem_lai", None)
        else:
            out[p["folder"]] = ("on", None)
    return out, {"median_views": med, "du_an_du_tuoi": len(eligible), "so_ngay_danh_gia": days_needed,
                 "du_so_sanh": compare}


def _counts(conn, period: str, by_space=False, folder=None) -> dict:
    """{folder or space id: [views, saves]} of published photos in the period."""
    key = "s.id" if by_space else FOLDER
    out = {}
    for k, loai, n in _rows(conn, f"SELECT {key}, e.loai, count(*) FROM su_kien e JOIN space s ON s.id = e.space_id "
                                  "WHERE s.review_status = 'published' AND e.loai IN ('xem_khong_gian', 'luu_anh') "
                                  f"AND e.created_at > now() - %s::interval AND (%s::text IS NULL OR {FOLDER} = %s) "
                                  "GROUP BY 1, 2", (period, folder, folder)):
        out.setdefault(k, [0, 0])[0 if loai == "xem_khong_gian" else 1] = n
    return out


def _leads(conn, period: str) -> dict:
    """{folder: distinct leads in the period} from the three sources."""
    return dict(_rows(conn, f"""
        SELECT folder, count(DISTINCT id) FROM (
            SELECT l.id, replace(l.ngu_canh->>'du_an', '-', '_') AS folder FROM lead l
             WHERE l.ngu_canh->>'du_an' IS NOT NULL AND l.created_at > now() - %(p)s::interval
            UNION
            SELECT l.id, {FOLDER} FROM lead l JOIN space s
                ON (l.ngu_canh->>'space_id') ~ '^[0-9]{{1,9}}$' AND s.id = (l.ngu_canh->>'space_id')::int
             WHERE l.created_at > now() - %(p)s::interval
            UNION
            SELECT l.id, {FOLDER} FROM lead l JOIN bo_suu_tap_anh a ON a.bo_suu_tap_id = l.bo_suu_tap_id
              JOIN space s ON s.id = a.space_id
             WHERE l.created_at > now() - %(p)s::interval
        ) x GROUP BY folder""", {"p": period}))


def overview(conn, days: int, user_id=None) -> dict:
    period = f"{int(days)} days"
    projects = {f: {"folder": f, "so_anh": n} for f, n in _rows(
        conn, f"SELECT {FOLDER}, count(*) FROM space s WHERE s.review_status = 'published' GROUP BY 1")}

    published = {f: (d, a) for f, d, a in _rows(conn, f"""
        SELECT {FOLDER}, min(r.at) FILTER (WHERE r.action = 'advance' AND r.detail->>'to' = 'published'),
               min(r.at) FILTER (WHERE r.action = 'ingest')
          FROM review_log r JOIN space s ON s.id = r.space_id GROUP BY 1""")}
    now = _rows(conn, "SELECT now()")[0][0]
    counts, window, leads = _counts(conn, period), _counts(conn, f"{WINDOW} days"), _leads(conn, period)

    for f, p in projects.items():
        pub, ingest = published.get(f, (None, None))
        when = pub or ingest
        xem, luu = counts.get(f, [0, 0])
        p.update({"ngay_dang": when.isoformat() if when else None, "ngay_dang_uoc_tinh": pub is None and when is not None,
                  "tuoi": (now - when).days if when else None, "luot_xem": xem, "luot_luu": luu,
                  "ti_le_luu": round(100 * luu / xem) if xem else None, "khach_tiem_nang": leads.get(f, 0),
                  "luot_xem_cua_so": window.get(f, [0, 0])[0]})

    status, so_sanh = statuses(list(projects.values()), review_days())
    for f, p in projects.items():
        p["trang_thai"], p["con_ngay"] = status[f]
    if user_id is not None:  # after the statuses: "my projects" are still compared with every project
        mine = {f for (f,) in _rows(conn, f"SELECT DISTINCT {FOLDER} FROM review_log r JOIN space s ON s.id = r.space_id "
                                          "WHERE r.action = 'ingest' AND r.user_id = %s", (user_id,))}
        projects = {f: p for f, p in projects.items() if f in mine}

    order = {"can_xem_lai": 0, "dang_theo_doi": 1, "on": 1}
    rows = sorted(projects.values(), key=lambda p: (order[p["trang_thai"]], -p["luot_xem"], p["folder"]))
    demo = bool(_rows(conn, "SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')")[0][0])
    return {"days": int(days), "projects": rows, "so_sanh": so_sanh, "co_du_lieu_mo_phong": demo}


def _goi_y(ma, text, ids, folder):
    return {"ma": ma, "text": text, "anh": ids, "so_anh": len(ids), "link": f"/quan-tri#p-{folder}"}


def detail(conn, folder: str, days: int):
    """{project, photos, goi_y} of one folder, or None when it has no published photo."""
    ov = overview(conn, days)
    project = next((p for p in ov["projects"] if p["folder"] == folder), None)
    if project is None:
        return None
    counts = _counts(conn, f"{int(days)} days", by_space=True, folder=folder)
    photos = [{"id": i, "relative_path": rp, "caption": cap, "design_style": st, "style_confidence": conf,
               "luot_xem": counts.get(i, [0, 0])[0], "luot_luu": counts.get(i, [0, 0])[1]}
              for i, rp, cap, st, conf in _rows(conn, f"SELECT s.id, s.relative_path, s.caption, s.design_style, "
                                                      f"s.style_confidence FROM space s WHERE {FOLDER} = %s "
                                                      "AND s.review_status = 'published' ORDER BY s.id", (folder,))]
    for p in photos:
        p["chua_ai_xem"] = p["luot_xem"] == 0
    photos.sort(key=lambda p: (-p["luot_xem"], -p["luot_luu"], p["id"]))
    ids = [p["id"] for p in photos]

    goi_y = []
    tagged = {d for (d,) in _rows(conn, "SELECT DISTINCT d.ma_dinh_danh FROM space_gia_tri sg "
                                        "JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id "
                                        "JOIN chieu_phan_loai d ON d.id = g.chieu_id "
                                        "WHERE sg.space_id = ANY(%s) AND d.ma_dinh_danh = ANY(%s)", (ids, list(TAG_DIMS)))}
    names = dict(_rows(conn, "SELECT ma_dinh_danh, ten FROM chieu_phan_loai WHERE ma_dinh_danh = ANY(%s)", (list(TAG_DIMS),)))
    for dim, ma in TAG_DIMS.items():
        if dim not in tagged:
            ten = names.get(dim, dim)
            goi_y.append(_goi_y(ma, f"Chưa ảnh nào có nhãn “{ten}”, nên khách lọc theo {ten.lower()} sẽ không thấy "
                                    "dự án này. Gắn nhãn cho cả dự án.", [], folder))

    unclear = [p["id"] for p in photos if (p["design_style"] or "").lower() == "khac"
               or (p["style_confidence"] is not None and p["style_confidence"] < LOW_CONFIDENCE)]
    if unclear:
        goi_y.append(_goi_y("phong_cach_chua_ro", f"{len(unclear)} ảnh có phong cách “Khác” hoặc AI chưa chắc chắn. "
                                                  "Kiểm tra và chọn lại phong cách.", unclear, folder))

    per_project = [n for (n,) in _rows(conn, f"SELECT count(*) FROM space s WHERE s.review_status = 'published' "
                                             f"GROUP BY {FOLDER}")]
    med_photos = median(per_project)
    if len(photos) < FEW_PHOTOS * med_photos:
        goi_y.append(_goi_y("it_anh", f"Dự án chỉ có {len(photos)} ảnh đã đăng, ít hơn nhiều so với các dự án khác "
                                      f"(trung vị {med_photos:g}). Đăng thêm ảnh.", [], folder))

    unseen = [p["id"] for p in photos if p["chua_ai_xem"]]
    if unseen and project["luot_xem"] > 0:
        goi_y.append(_goi_y("anh_chua_ai_xem", f"{len(unseen)} ảnh chưa ai xem trong kỳ. Xem lại tiêu đề, chú thích "
                                               "hoặc thứ tự của các ảnh này.", unseen, folder))

    lengths = [len(p["caption"] or "") for p in photos]
    med_len = median(lengths) if lengths else 0
    short = [p["id"] for p in photos if len(p["caption"] or "") < SHORT_CAPTION * med_len]
    if short:
        goi_y.append(_goi_y("mo_ta_ngan", f"{len(short)} ảnh có chú thích ngắn hơn hẳn các ảnh khác của dự án. "
                                          "Viết thêm mô tả.", short, folder))

    return {"days": int(days), "project": project, "photos": photos, "goi_y": goi_y,
            "co_du_lieu_mo_phong": ov["co_du_lieu_mo_phong"]}
