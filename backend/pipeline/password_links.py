"""Password links (UC24; seq-19 steps 7-11; change account-invites-reset): an invitation to activate an account an
admin created (72 h) or a reset of a forgotten password (1 h). Single use; issuing a link voids the account's other
active links; only a sha256 of the random code is stored. A reset also ends the account's open sessions (phien_tu,
the same mechanism as a lock)."""

import hashlib
import os
import secrets
from datetime import timedelta

from psycopg.rows import dict_row

TTL = {"moi": timedelta(hours=72), "dat_lai": timedelta(hours=1)}
REASON_VI = {"khong_hop_le": "Liên kết không hợp lệ.", "het_han": "Liên kết đã hết hạn.",
             "da_dung": "Liên kết đã được sử dụng.", "da_huy": "Liên kết đã bị thay bằng liên kết mới hoặc đã bị huỷ.",
             "khoa": "Tài khoản đang bị khoá."}


class LinkError(Exception):
    def __init__(self, reason):
        super().__init__(REASON_VI[reason])
        self.reason = reason


def _hash(code: str) -> str:
    return hashlib.sha256((code or "").encode()).hexdigest()


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def void(conn, user_id, loai=None):
    conn.execute("UPDATE ma_dat_mat_khau SET da_huy = now() WHERE tai_khoan_id = %s AND da_dung IS NULL AND da_huy IS NULL "
                 "AND (%s::text IS NULL OR loai = %s)", (user_id, loai, loai))


def issue(conn, user_id, loai, by=None) -> str:
    """A new link code for the account; its other active links stop working."""
    code = secrets.token_urlsafe(32)
    void(conn, user_id)
    conn.execute("INSERT INTO ma_dat_mat_khau (tai_khoan_id, loai, ma_bam, het_han, tao_boi) VALUES (%s, %s, %s, now() + %s, %s)",
                 (user_id, loai, _hash(code), TTL[loai], by))
    return code


def check(conn, code, lock=False) -> dict:
    """{id, user_id, loai, email} of a usable link, else LinkError(reason)."""
    if not code or len(code) > 200:
        raise LinkError("khong_hop_le")
    row = _cur(conn).execute(
        "SELECT m.id, m.tai_khoan_id AS user_id, m.loai, m.het_han < now() AS het_han, m.da_dung, m.da_huy, u.email, u.bi_khoa "
        "FROM ma_dat_mat_khau m JOIN app_user u ON u.id = m.tai_khoan_id WHERE m.ma_bam = %s"
        + (" FOR UPDATE OF m, u" if lock else ""), (_hash(code),)).fetchone()
    if not row:
        raise LinkError("khong_hop_le")
    for bad in ("da_dung", "da_huy", "het_han"):
        if row[bad]:
            raise LinkError(bad)
    if row["bi_khoa"]:
        raise LinkError("khoa")
    return {"id": row["id"], "user_id": row["user_id"], "loai": row["loai"], "email": row["email"]}


def use(conn, code, password_hash: str) -> dict:
    """Set the password from a link; the link is used, the account's other links void; a reset ends old sessions."""
    link = check(conn, code, lock=True)
    conn.execute("UPDATE ma_dat_mat_khau SET da_dung = now() WHERE id = %s", (link["id"],))
    void(conn, link["user_id"])
    conn.execute("UPDATE app_user SET password_hash = %s" + (", phien_tu = clock_timestamp()" if link["loai"] == "dat_lai" else "")
                 + " WHERE id = %s", (password_hash, link["user_id"]))
    return link


def link_url(code: str) -> str:
    """The code goes after '#': it is not sent to the server when the page is opened."""
    return f"{os.getenv('D3_FRONTEND_URL', '').rstrip('/')}/dat-mat-khau#ma={code}"


def mask(email: str) -> str:
    name, _, domain = (email or "").partition("@")
    return (name[:1] + "***@" + domain) if domain else "***"
