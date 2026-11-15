"""Chat conversations (seq-3 step 18; class-4 HoiThoai / TinNhan; roadmap 2.8).

    stored      every conversation, anonymously; linked to a session only when the browser sends its session id,
                which it does only after the visitor accepted collection (the row is created then, as /events does)
    masked      phone numbers and email addresses in visitor messages, before storing (a lead keeps its own contact)
    kept        90 days after the last message, then purged
    constraints project_type / space_type / area_m2 / design_style collected across the conversation; a newer value
                replaces an older one, nothing is ever cleared
The id is random (32 hex); holding it is what lets a visitor read or delete their conversation."""

import re
import uuid

from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

KEEP_DAYS = 90
HISTORY_TURNS = 4  # messages handed to the model, as photo RAG already uses
CARRY = ("project_type", "space_type", "area_m2", "design_style")
ID = re.compile(r"^[0-9a-f]{32}$")
PHONE = re.compile(r"(?<![\d+])(?:\+84|0)(?:[\s.\-]?\d){9}(?!\d)")
EMAIL = re.compile(r"[^\s@<>()]+@[^\s@<>()]+\.[A-Za-z]{2,}")
PER_PAGE = 50
FILTERS = ("tat_ca", "chua_tra_loi", "lead")


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def mask(text: str) -> str:
    return PHONE.sub("[số điện thoại]", EMAIL.sub("[email]", text or ""))


def merge(old: dict | None, new: dict | None) -> dict:
    out = {k: v for k, v in (old or {}).items() if k in CARRY}
    out.update({k: v for k, v in (new or {}).items() if k in CARRY and v is not None})
    return out


def valid(hid) -> bool:
    return isinstance(hid, str) and bool(ID.match(hid))


def start_or_get(conn, hid: str | None, phien_id: str | None = None):
    """(id, constraints, last turns as [{role, content}]). A missing, malformed or unknown id starts a new one.
    phien_id: the consented session id (the client sends it only after consent; same trust as /events)."""
    row = _rows(conn, "SELECT id, rang_buoc, phien_id FROM hoi_thoai WHERE id = %s", (hid,)) if valid(hid) else []
    consented = bool(phien_id)
    if consented:  # a visitor may chat before any tracked view created the session row
        conn.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true) ON CONFLICT DO NOTHING",
                     (phien_id,))
    if not row:
        hid = uuid.uuid4().hex
        conn.execute("INSERT INTO hoi_thoai (id, phien_id) VALUES (%s, %s)", (hid, phien_id if consented else None))
        return hid, {}, []
    _, rang_buoc, linked = row[0]
    if consented and not linked:  # accepted the banner mid-conversation
        conn.execute("UPDATE hoi_thoai SET phien_id = %s WHERE id = %s", (phien_id, hid))
    turns = _rows(conn, "SELECT vai_tro, noi_dung FROM (SELECT id, vai_tro, noi_dung FROM tin_nhan WHERE hoi_thoai_id = %s "
                        "ORDER BY id DESC LIMIT %s) t ORDER BY id", (hid, HISTORY_TURNS))
    return hid, rang_buoc or {}, [{"role": "user" if r == "khach" else "assistant", "content": c} for r, c in turns]


def add_turn(conn, hid, question, answer, sources, best, answered, rang_buoc, chu_de_cam=None):
    """chu_de_cam: {id, ten, o} when a forbidden topic replaced the answer; kept for staff only."""
    conn.execute("INSERT INTO tin_nhan (hoi_thoai_id, vai_tro, noi_dung) VALUES (%s, 'khach', %s)", (hid, mask(question)))
    conn.execute("INSERT INTO tin_nhan (hoi_thoai_id, vai_tro, noi_dung, nguon, diem_cao_nhat, tra_loi_duoc, chu_de_cam) "
                 "VALUES (%s, 'tro_ly', %s, %s, %s, %s, %s)",
                 (hid, answer, Jsonb(sources or []), best, answered, Jsonb(chu_de_cam) if chu_de_cam else None))
    conn.execute("UPDATE hoi_thoai SET cap_nhat = now(), so_tin_nhan = so_tin_nhan + 2, "
                 "chua_tra_loi = chua_tra_loi + %s, rang_buoc = %s WHERE id = %s",
                 (0 if answered else 1, Jsonb(merge({}, rang_buoc)), hid))


def link_lead(conn, hid, lead_id, handoff: bool):
    conn.execute("UPDATE lead SET hoi_thoai_id = %s WHERE id = %s", (hid, lead_id))
    if handoff:
        conn.execute("UPDATE hoi_thoai SET da_chuyen_nguoi_that = true WHERE id = %s", (hid,))


def _messages(conn, hid, staff=False):
    rows = _rows(conn, "SELECT vai_tro, noi_dung, nguon, diem_cao_nhat, tra_loi_duoc, thoi_diem, chu_de_cam FROM tin_nhan "
                       "WHERE hoi_thoai_id = %s ORDER BY id", (hid,))
    out = []
    for vai_tro, noi_dung, nguon, diem, ok, at, cam in rows:
        m = {"vai_tro": vai_tro, "noi_dung": noi_dung, "nguon": nguon or [], "thoi_diem": at}
        if staff:  # the visitor never learns which topic stopped an answer
            m.update({"diem_cao_nhat": diem, "tra_loi_duoc": ok, "chu_de_cam": cam})
        out.append(m)
    return out


def read(conn, hid):
    """The visitor's own conversation, or None."""
    if not valid(hid) or not _rows(conn, "SELECT 1 FROM hoi_thoai WHERE id = %s", (hid,)):
        return None
    return {"hoi_thoai_id": hid, "tin_nhan": _messages(conn, hid)}


def delete(conn, hid):
    if valid(hid):
        conn.execute("DELETE FROM hoi_thoai WHERE id = %s", (hid,))


def purge(conn, days: int = KEEP_DAYS) -> int:
    return conn.execute("DELETE FROM hoi_thoai WHERE cap_nhat < now() - make_interval(days => %s)", (days,)).rowcount


_COLS = ("id", "bat_dau", "cap_nhat", "so_tin_nhan", "chua_tra_loi", "da_chuyen_nguoi_that", "rang_buoc", "lead_id")
_SELECT = ("SELECT h.id, h.bat_dau, h.cap_nhat, h.so_tin_nhan, h.chua_tra_loi, h.da_chuyen_nguoi_that, h.rang_buoc, "
           "(SELECT min(l.id) FROM lead l WHERE l.hoi_thoai_id = h.id) FROM hoi_thoai h ")


def list_for_staff(conn, loc: str = "tat_ca", days: int = 30, offset: int = 0) -> dict:
    where = ["h.cap_nhat > now() - make_interval(days => %s)", "h.so_tin_nhan > 0"]
    if loc == "chua_tra_loi":
        where.append("h.chua_tra_loi > 0")
    elif loc == "lead":
        where.append("EXISTS (SELECT 1 FROM lead l WHERE l.hoi_thoai_id = h.id)")
    clause = " WHERE " + " AND ".join(where)
    total = _rows(conn, "SELECT count(*) FROM hoi_thoai h" + clause, (days,))[0][0]
    rows = _rows(conn, _SELECT + clause + " ORDER BY h.cap_nhat DESC LIMIT %s OFFSET %s", (days, PER_PAGE, offset))
    items = [dict(zip(_COLS, r)) for r in rows]
    firsts = dict(_rows(conn, "SELECT DISTINCT ON (hoi_thoai_id) hoi_thoai_id, noi_dung FROM tin_nhan "
                              "WHERE hoi_thoai_id = ANY(%s) AND vai_tro = 'khach' ORDER BY hoi_thoai_id, id",
                        ([i["id"] for i in items],)))
    for i in items:
        i["cau_dau"] = firsts.get(i["id"], "")
    return {"tong": total, "items": items}


def detail_for_staff(conn, hid):
    rows = _rows(conn, _SELECT + "WHERE h.id = %s", (hid,)) if valid(hid) else []
    if not rows:
        return None
    return {**dict(zip(_COLS, rows[0])), "tin_nhan": _messages(conn, hid, staff=True)}
