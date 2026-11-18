"""Homepage "Đang được quan tâm" (tracking-pipeline; act-3 "Điều chỉnh gợi ý trên trang chủ").

Values are taken in this order, never hidden ones, never 'khac', only dimensions shown to visitors:
  1. values the leadership prioritised (oldest setting first);
  2. with personalisation consent, the values most frequent in the visitor's own session;
  3. values with a stored rising / new trend on the last processed day;
  4. the highest-scoring values of the last 30 processed days.
Each value gives at most 2 published spaces (most viewed in 30 days first), 8 spaces in all, none the visitor viewed.
"""

from collections import Counter
from datetime import timedelta

from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from pipeline import trends

LIMIT, PER_VALUE, WINDOW = 8, 2, 30
MODES = ("tu_dong", "uu_tien", "an")


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def _visible(conn) -> dict:
    """{'dim:value': (dimension code, dimension name, value name)} for visitor-facing dimensions, without 'khac'."""
    return {f"{d}:{v}": (d, dn, vn) for d, dn, v, vn in _rows(
        conn, "SELECT c.ma_dinh_danh, c.ten, g.ma_dinh_danh, g.ten FROM gia_tri_phan_loai g JOIN chieu_phan_loai c ON c.id = g.chieu_id "
              "WHERE c.hien_thi_cho_khach") if not trends.is_khac(f"{d}:{v}")}


def settings(conn) -> dict:
    return {v: m for v, m in _rows(conn, "SELECT gia_tri, che_do FROM goi_y_trang_chu")}


def _order(conn, phien_id) -> tuple[list[tuple[str, str]], set]:
    """[(value, source)] in priority order, and the space ids the visitor already viewed."""
    visible, modes = _visible(conn), settings(conn)
    hidden = {v for v, m in modes.items() if m == "an"}
    order, seen_vals = [], set()

    def add(values, source):
        for v in values:
            if v in visible and v not in hidden and v not in seen_vals:
                order.append((v, source))
                seen_vals.add(v)

    add([v for (v,) in _rows(conn, "SELECT gia_tri FROM goi_y_trang_chu WHERE che_do = 'uu_tien' ORDER BY luc")], "uu_tien")
    viewed = set()
    if phien_id and _rows(conn, "SELECT 1 FROM phien_truy_cap WHERE id = %s AND ca_nhan_hoa", (phien_id,)):
        counts = Counter()
        for space_id, vals in _rows(conn, "SELECT space_id, gia_tri FROM su_kien WHERE phien_id = %s "
                                          "AND loai IN ('xem_khong_gian', 'luu_anh')", (phien_id,)):
            viewed.add(space_id)
            counts.update(vals)
        add([v for v, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))], "ca_nhan")
    end = trends.last_day(conn)
    if end:
        add([v for (v,) in _rows(conn, "SELECT gia_tri FROM tk_xu_huong WHERE ngay_tinh = %s AND xu_huong IN ('dang_tang', 'moi_noi') "
                                       "ORDER BY xu_huong = 'dang_tang' DESC, thay_doi DESC NULLS LAST, gia_tri", (end,))], "xu_huong")
        scored = _rows(conn, "SELECT gia_tri, sum(so_xem), sum(so_luu), sum(so_brief) FROM tk_gia_tri_ngay "
                             "WHERE ngay > %s GROUP BY 1", (end - timedelta(days=WINDOW),))
        ranked = sorted(((trends.score(x, l, b), v) for v, x, l, b in scored), key=lambda s: (-s[0], s[1]))
        add([v for s, v in ranked if s > 0], "diem")
    return order, viewed


def label(dim: str, dim_name: str, name: str, source: str) -> str:
    what = name if dim == "khong_gian" else f"{dim_name} {name}"
    return f"Vì bạn đã xem {what[0].lower() + what[1:]}" if source == "ca_nhan" else f"{what} đang được quan tâm"


def suggestions(conn, phien_id: str | None = None) -> list[dict]:
    order, viewed = _order(conn, phien_id)
    if not order:
        return []
    visible = _visible(conn)
    end = trends.last_day(conn)
    since = (end - timedelta(days=WINDOW)) if end else None
    chosen, out = set(viewed), []
    for v, source in order:
        dim, code = v.split(":", 1)
        rows = _rows(conn, """
            SELECT s.id, s.relative_path, s.alt_text FROM space s
              JOIN space_gia_tri sg ON sg.space_id = s.id JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id
              JOIN chieu_phan_loai c ON c.id = g.chieu_id
             WHERE s.review_status = 'published' AND c.ma_dinh_danh = %s AND g.ma_dinh_danh = %s AND NOT s.id = ANY(%s)
             ORDER BY (SELECT COALESCE(sum(so_xem), 0) FROM tk_khong_gian_ngay k WHERE k.space_id = s.id
                        AND (%s::date IS NULL OR k.ngay > %s)) DESC, s.id
             LIMIT %s""", (dim, code, list(chosen), since, since, PER_VALUE))
        _, dim_name, name = visible[v]
        for sid, path, alt in rows:
            chosen.add(sid)
            out.append({"id": sid, "relative_path": path, "alt_text": alt, "nhan": label(dim, dim_name, name, source),
                        "ly_do": {"chieu": dim, "ma": code, "ten": name, "nguon": source}})
            if len(out) == LIMIT:
                return out
    return out


def set_mode(conn, value: str, mode: str, user_id: int) -> dict:
    """tu_dong removes the setting; uu_tien / an set it. Logged with who and when. KeyError for an unknown value."""
    if mode not in MODES:
        raise ValueError(mode)
    visible = _visible(conn)
    if value not in visible:
        raise KeyError(value)
    before = settings(conn).get(value, "tu_dong")
    if mode == "tu_dong":
        conn.execute("DELETE FROM goi_y_trang_chu WHERE gia_tri = %s", (value,))
    else:
        conn.execute("INSERT INTO goi_y_trang_chu (gia_tri, che_do, nguoi_id) VALUES (%s, %s, %s) ON CONFLICT (gia_tri) "
                     "DO UPDATE SET che_do = EXCLUDED.che_do, nguoi_id = EXCLUDED.nguoi_id, luc = now()", (value, mode, user_id))
    if before != mode:
        conn.execute("INSERT INTO goi_y_trang_chu_nhat_ky (gia_tri, che_do_cu, che_do_moi, nguoi_id) VALUES (%s, %s, %s, %s)",
                     (value, before, mode, user_id))
    return {"gia_tri": value, "che_do": mode}


def admin_view(conn) -> dict:
    visible = _visible(conn)
    rows = _rows(conn, "SELECT h.gia_tri, h.che_do, u.email, h.luc FROM goi_y_trang_chu h LEFT JOIN app_user u ON u.id = h.nguoi_id "
                       "ORDER BY h.luc")
    return {"cai_dat": [{"gia_tri": v, "che_do": m, "ten": visible.get(v, (None, None, v))[2], "chieu": visible.get(v, (None, "",))[1],
                         "boi": who, "luc": at.isoformat()} for v, m, who, at in rows],
            "xem_truoc": suggestions(conn)}
