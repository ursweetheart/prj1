"""New-lead notices (seq-5 #11–12, dfd-2-4 4.2). Email via SMTP when configured, otherwise a log line.
Never raises: a mail problem must not fail the visitor's request or lose the lead (the lead is already stored).

Env: D3_SMTP_HOST, D3_SMTP_PORT (587, STARTTLS), D3_SMTP_USER, D3_SMTP_PASSWORD, D3_SMTP_FROM, D3_SALES_EMAIL."""

import logging
import os
import smtplib
from email.message import EmailMessage

from pipeline.leads import get_lead, profile_summary

log = logging.getLogger("d3.leads")
log.setLevel(logging.INFO)
if not log.handlers:  # uvicorn configures only its own loggers; without this the INFO notice never reaches the log
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     %(name)s %(message)s"))
    log.addHandler(_h)

SOURCE_VI = {"form": "Form liên hệ", "chat": "Trợ lý chat", "brief": "Bộ sưu tập (brief)", "estimate": "Ước tính chi phí"}
INTENT_VI = {"price": "hỏi giá", "appointment": "xin hẹn", "handoff": "trợ lý chưa trả lời được"}


def _smtp_ready() -> bool:
    return bool(os.getenv("D3_SMTP_HOST"))


def _send(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = os.getenv("D3_SMTP_FROM") or os.getenv("D3_SMTP_USER") or "no-reply@d3studio.local"
    msg["To"], msg["Subject"] = to, subject
    msg.set_content(body)
    with smtplib.SMTP(os.environ["D3_SMTP_HOST"], int(os.getenv("D3_SMTP_PORT", "587")), timeout=15) as s:
        s.starttls()
        if os.getenv("D3_SMTP_USER"):
            s.login(os.environ["D3_SMTP_USER"], os.getenv("D3_SMTP_PASSWORD", ""))
        s.send_message(msg)


def _context_line(ngu_canh: dict | None) -> str:
    c = ngu_canh or {}
    if c.get("du_an"):
        return f"dự án {c['du_an']} (trang {c.get('trang', '/du-an/' + c['du_an'])})"
    if c.get("space_id"):
        return f"không gian #{c['space_id']} (trang {c.get('trang', '/khong-gian/' + str(c['space_id']))})"
    return f"trang {c.get('trang') or '(không rõ)'}"


def notify_new_lead(lead_id: int):
    """Tell the consultants: source, contact, context, profile summary. Log only id/source/summary (no phone, email)."""
    try:
        lead = get_lead(lead_id)
        if not lead:
            return
        summary = profile_summary(lead["ho_so_hanh_vi"])
        source = SOURCE_VI.get(lead["nguon"], lead["nguon"])
        sales = os.getenv("D3_SALES_EMAIL")
        if not (_smtp_ready() and sales):
            log.info("lead %s (%s) mới%s — chưa cấu hình email, xem tại /khach-hang",
                     lead_id, lead["nguon"], f": {summary}" if summary else "")
            return
        who = lead["ho_ten"] or "Khách"
        lines = [f"Nguồn: {source}" + (f" ({INTENT_VI.get(lead['intent'], lead['intent'])})" if lead["intent"] else ""),
                 f"Họ tên: {who}",
                 f"Điện thoại: {lead['so_dien_thoai'] or '—'}",
                 f"Email: {lead['email'] or '—'}"]
        if lead["contact"]:
            lines.append(f"Liên hệ để lại trong chat: {lead['contact']}")
        lines.append(f"Từ: {_context_line(lead['ngu_canh'])}")
        if lead["loi_nhan"]:
            lines += ["", "Lời nhắn:", lead["loi_nhan"]]
        if summary:
            lines += ["", f"Sở thích (khách đồng ý gửi): {summary}"]
            lines += [f"  - #{s['id']} {s['relative_path']}" for s in lead["ho_so_hanh_vi"].get("spaces", [])]
        if lead["conversation"]:
            lines += ["", "Hội thoại:"] + [f"  {'Khách' if m.get('role') == 'user' else 'Trợ lý'}: {m.get('content')}"
                                          for m in lead["conversation"] if isinstance(m, dict)]
        lines += ["", f"Xem tất cả khách tiềm năng: {os.getenv('D3_FRONTEND_URL', '').rstrip('/')}/khach-hang"]
        _send(sales, f"[D3] Khách tiềm năng mới #{lead_id} — {source}: {who}", "\n".join(lines))
    except Exception:
        log.exception("lead %s: could not notify the consultants", lead_id)


def confirm_to_visitor(lead_id: int):
    """Receipt to the visitor's own email (only when given and SMTP is set). No behaviour profile in it."""
    try:
        lead = get_lead(lead_id)
        if not (lead and lead["email"] and _smtp_ready()):
            return
        body = (f"Chào {lead['ho_ten'] or 'anh/chị'},\n\n"
                "D3 Studio đã nhận yêu cầu tư vấn của anh/chị. Tư vấn viên sẽ liên hệ "
                f"qua số {lead['so_dien_thoai'] or 'anh/chị đã để lại'} trong thời gian sớm nhất.\n\n"
                "Cảm ơn anh/chị đã quan tâm.\nD3 Studio")
        _send(lead["email"], "D3 Studio đã nhận yêu cầu tư vấn của anh/chị", body)
    except Exception:
        log.exception("lead %s: could not send the visitor confirmation", lead_id)
