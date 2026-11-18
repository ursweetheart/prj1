"""Weekly report (UC23; seq-18 steps 1-7; roadmap 3.4). Built from the same counts as the two dashboards and sent every
Monday from 08:00 Vietnam time to active sales / lead_architect / admin accounts that did not turn it off.

    week          the last full Monday-Sunday week in UTC+7 (Vietnam has no daylight saving)
    once a week   a bao_cao_tuan row is claimed (INSERT ... ON CONFLICT DO NOTHING) and committed before any mail goes
                  out, so a restart or a second process never sends the same week twice; a crash mid-send leaves
                  'dang_gui', visible in the log, and is not retried
    no SMTP       the text goes to the 'd3.report' log and the week is recorded as 'chi_ghi_log'
Only counts leave this module: never a visitor's name, contact, account or session id."""

import logging
import os
from datetime import datetime, time, timedelta, timezone

from psycopg.rows import tuple_row

from pipeline import notify, project_stats, trends

VN = timezone(timedelta(hours=7))
SEND_AT = time(8, 0)
ROLES = ("sales", "lead_architect", "admin")
TOP_DIMS = (("phong_cach", "Phong cách"), ("khong_gian", "Loại không gian"))
TOP_N = 3
MAX_ALERTS = 8  # the dashboard has the full list; the email keeps the strongest (trends sorts them)
TREND_VI = {"dang_tang": "đang tăng", "moi_noi": "mới nổi", "dang_giam": "đang giảm"}

log = logging.getLogger("d3.report")
log.setLevel(logging.INFO)
if not log.handlers:  # uvicorn configures only its own loggers
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     %(name)s %(message)s"))
    log.addHandler(_h)


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def week_bounds(now: datetime):
    """(start, end) of the last full week before `now`: Monday 00:00 to the next Monday 00:00, UTC+7, aware."""
    local = now.astimezone(VN)
    this_monday = datetime.combine(local.date() - timedelta(days=local.weekday()), time(0), VN)
    return this_monday - timedelta(days=7), this_monday


def due(now: datetime) -> bool:
    """True from Monday 08:00 (UTC+7) to the end of Sunday: the current week's report may go out."""
    local = now.astimezone(VN)
    return local.weekday() > 0 or local.time() >= SEND_AT


def _fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def change(this: int, before: int) -> str:
    if before:
        d = round(100 * (this - before) / before)
        return f"{'+' if d > 0 else ''}{d}%"
    return "mới" if this else "–"


def _totals(conn, start, end) -> dict:
    """Views and saves (consented + anonymous daily counts), briefs sent and leads by source in [start, end)."""
    # tracking-pipeline (seq-18 b2-b3): from the analytics store; [start, end) are UTC+7 midnights, so whole days
    d0, d1 = start.astimezone(VN).date(), end.astimezone(VN).date()
    xem, luu = (int(x or 0) for x in _rows(conn, "SELECT sum(so_xem), sum(so_luu) FROM tk_khong_gian_ngay "
                                                  "WHERE ngay >= %s AND ngay < %s", (d0, d1))[0])
    anon = dict(_rows(conn, "SELECT loai, sum(so_luong) FROM su_kien_an_danh WHERE ngay >= %s AND ngay < %s GROUP BY loai",
                      (d0, d1)))
    briefs, leads = 0, {}
    for b, ld in _rows(conn, "SELECT so_brief, lead FROM tk_tong_ngay WHERE ngay >= %s AND ngay < %s", (d0, d1)):
        briefs += b
        for s, n in ld.items():
            leads[s] = leads.get(s, 0) + n
    return {"luot_xem": xem + int(anon.get("xem_khong_gian") or 0), "luot_luu": luu + int(anon.get("luu_anh") or 0),
            "brief": briefs, "lead": {s: leads.get(s, 0) for s in trends.SOURCES}}


def _site() -> str:
    return os.getenv("D3_FRONTEND_URL", "").rstrip("/")


def build(conn, now: datetime) -> dict:
    """{tuan_bat_dau, tieu_de, noi_dung, so_lieu} for the last full week before `now`."""
    start, end = week_bounds(now)
    cur, prev = _totals(conn, start, end), _totals(conn, start - timedelta(days=7), start)
    tr = trends.overview(conn, 7)
    ps = project_stats.overview(conn, 30)
    last = end - timedelta(days=1)
    title = f"[D3] Báo cáo tuần {start:%d/%m} – {last:%d/%m/%Y}"

    lines = []
    if tr["co_du_lieu_mo_phong"]:
        lines += ["LƯU Ý: số liệu tuần này có cả dữ liệu MÔ PHỎNG (phiên demo), không phải khách thật.", ""]
    lines += [f"Báo cáo hoạt động tuần {start:%d/%m} – {last:%d/%m/%Y}, so với tuần trước.", "",
              "TỔNG QUAN",
              f"- Lượt xem: {_fmt(cur['luot_xem'])} ({change(cur['luot_xem'], prev['luot_xem'])})",
              f"- Lượt lưu ảnh: {_fmt(cur['luot_luu'])} ({change(cur['luot_luu'], prev['luot_luu'])})",
              f"- Bộ sưu tập đã gửi: {_fmt(cur['brief'])} ({change(cur['brief'], prev['brief'])})"]
    total_now, total_prev = sum(cur["lead"].values()), sum(prev["lead"].values())
    lines.append(f"- Khách tiềm năng: {_fmt(total_now)} ({change(total_now, total_prev)})")
    lines += [f"    {notify.SOURCE_VI.get(s, s)}: {cur['lead'][s]} ({change(cur['lead'][s], prev['lead'][s])})"
              for s in trends.SOURCES]

    lines += ["", "CẢNH BÁO XU HƯỚNG (7 ngày qua so với trung bình 4 tuần trước)"]
    if tr["canh_bao"]:
        for a in tr["canh_bao"][:MAX_ALERTS]:
            pct = f" ({'+' if (a['thay_doi'] or 0) > 0 else ''}{a['thay_doi']}%)" if a["thay_doi"] is not None else ""
            lines.append(f"- {a['chieu']} · {a['ten']}: {TREND_VI.get(a['xu_huong'], a['xu_huong'])}{pct}")
        if len(tr["canh_bao"]) > MAX_ALERTS:
            lines.append(f"- … và {len(tr['canh_bao']) - MAX_ALERTS} cảnh báo khác, xem trên bảng điều khiển.")
    else:
        lines.append("- Không có giá trị nào tăng hay giảm rõ rệt.")

    lines += ["", "ĐƯỢC QUAN TÂM NHẤT (7 ngày qua)"]
    for code, name in TOP_DIMS:
        dim = next((d for d in tr["chieu"] if d["ma"] == code), None)
        top = (dim or {}).get("gia_tri", [])[:TOP_N]
        lines.append(f"- {name}: " + (", ".join(f"{v['ten']} {v['ti_le']}%" for v in top) if top else "Không có hoạt động."))

    lines += ["", "DỰ ÁN CẦN XEM LẠI (lượt xem 30 ngày dưới một nửa trung vị)"]
    low = [p for p in ps["projects"] if p["trang_thai"] == "can_xem_lai"]
    if low:
        lines += [f"- {p['ten']}: {_fmt(p['luot_xem_cua_so'])} lượt xem" for p in low]
    else:
        lines.append("- Không có dự án nào cần xem lại.")

    site = _site()
    lines += ["", f"Xu hướng chi tiết: {site}/quan-tri/xu-huong", f"Hiệu quả từng dự án: {site}/quan-tri/hieu-qua", "",
              "Lượt xem và lượt lưu gồm cả khách không đồng ý theo dõi (chỉ đếm theo ngày); xu hướng và dự án chỉ tính "
              "khách đã đồng ý.",
              "Tắt báo cáo này: mở /quan-tri/xu-huong, bỏ chọn «Nhận báo cáo tuần qua email»."]
    return {"tuan_bat_dau": start.date(), "tieu_de": title, "noi_dung": "\n".join(lines),
            "so_lieu": {"tuan_nay": cur, "tuan_truoc": prev}}


def recipients(conn) -> list[str]:
    """Active sales / lead_architect / admin accounts with the report on; placeholder addresses skipped."""
    return [e for (e,) in _rows(conn, "SELECT email FROM app_user WHERE role = ANY(%s) AND NOT bi_khoa AND nhan_bao_cao_tuan "
                                      "AND email NOT LIKE '%%.invalid' ORDER BY id", (list(ROLES),))]


def send_week(conn, now: datetime, force_to: str | None = None):
    """Send the last full week's report once. force_to: a test copy to that address only, nothing recorded.
    Returns the bao_cao_tuan row as a dict ({'gui_toi': ...} for a test), or None when the week was already taken."""
    report = build(conn, now)
    if force_to:
        notify._send(force_to, "[Gửi thử] " + report["tieu_de"], report["noi_dung"])
        log.info("weekly report %s: test copy sent", report["tuan_bat_dau"])
        return {"gui_toi": force_to}

    claimed = _rows(conn, "INSERT INTO bao_cao_tuan (tuan_bat_dau, tieu_de, noi_dung) VALUES (%s, %s, %s) "
                          "ON CONFLICT DO NOTHING RETURNING tuan_bat_dau",
                    (report["tuan_bat_dau"], report["tieu_de"], report["noi_dung"]))
    conn.commit()  # the claim must be durable before any mail goes out
    if not claimed:
        return None

    to = recipients(conn)
    failed = 0
    if not notify._smtp_ready():
        result = "chi_ghi_log"
        log.info("weekly report %s (%d recipients, email not configured):\n%s\n%s",
                 report["tuan_bat_dau"], len(to), report["tieu_de"], report["noi_dung"])
    else:
        for addr in to:
            try:
                notify._send(addr, report["tieu_de"], report["noi_dung"])
            except Exception:
                failed += 1
                log.exception("weekly report %s: one recipient failed", report["tuan_bat_dau"])
        result = "loi" if not to or failed == len(to) else "loi_mot_phan" if failed else "da_gui"
        log.info("weekly report %s: %s, %d recipients, %d failed", report["tuan_bat_dau"], result, len(to), failed)
    row = conn.cursor().execute(
        "UPDATE bao_cao_tuan SET gui_luc = now(), so_nguoi_nhan = %s, so_loi = %s, ket_qua = %s WHERE tuan_bat_dau = %s "
        "RETURNING tuan_bat_dau, gui_luc, so_nguoi_nhan, so_loi, ket_qua, tieu_de",
        (len(to), failed, result, report["tuan_bat_dau"])).fetchone()
    conn.commit()
    keys = ("tuan_bat_dau", "gui_luc", "so_nguoi_nhan", "so_loi", "ket_qua", "tieu_de")
    return row if isinstance(row, dict) else dict(zip(keys, row))


def history(conn, n: int = 8) -> list:
    return [dict(zip(("tuan_bat_dau", "gui_luc", "so_nguoi_nhan", "so_loi", "ket_qua", "tieu_de"), r)) for r in _rows(
        conn, "SELECT tuan_bat_dau, gui_luc, so_nguoi_nhan, so_loi, ket_qua, tieu_de FROM bao_cao_tuan "
              "ORDER BY tuan_bat_dau DESC LIMIT %s", (n,))]
