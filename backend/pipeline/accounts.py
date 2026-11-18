"""Account admin (change user-admin; UC24, seq-19 b16-19): list accounts, change roles, lock and unlock.

Guards, checked inside the caller's transaction with the admin rows locked: an admin never changes their own role or
locks themselves, and the last active (unlocked) admin is never demoted or locked, so the site always keeps one.
A lock sets phien_tu = now, which auth.optional_user uses to refuse every token issued before it (open sessions end);
unlocking keeps phien_tu, so those tokens stay dead. A role change needs no sign-out: the role is read per request."""

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from pipeline import password_links

ROLES = ("visitor", "architect", "content", "sales", "lead_architect", "admin")
LIMIT, LOG_SHOWN = 500, 20
SELF = "Không tự đổi vai trò hoặc tự khoá tài khoản của chính mình."
LAST_ADMIN = "Phải còn ít nhất một quản trị viên đang hoạt động."


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


class Invalid(ValueError):
    pass


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def _log(conn, admin, account_id, action, before, after):
    conn.execute("INSERT INTO nhat_ky_tai_khoan (nguoi_dung_id, tai_khoan_id, hanh_dong, truoc, sau) VALUES (%s,%s,%s,%s,%s)",
                 (admin["id"] if admin else None, account_id, action, Jsonb(before), Jsonb(after)))


def _active_admins(conn, lock=False) -> list:
    sql = "SELECT id FROM app_user WHERE role = 'admin' AND NOT bi_khoa ORDER BY id" + (" FOR UPDATE" if lock else "")
    return [r["id"] for r in _cur(conn).execute(sql).fetchall()]


def _target(conn, user_id) -> dict:
    row = _cur(conn).execute("SELECT id, email, role, bi_khoa, ly_do_khoa FROM app_user WHERE id = %s FOR UPDATE",
                             (user_id,)).fetchone()
    if not row:
        raise NotFound("user not found")
    return row


def _guard(conn, admin, target, removes_admin: bool):
    if admin and target["id"] == admin["id"]:
        raise Conflict(SELF)
    if removes_admin and target["role"] == "admin" and not target["bi_khoa"]:
        active = _active_admins(conn, lock=True)  # locked rows: two admins cannot demote each other at once
        if active == [target["id"]]:
            raise Conflict(LAST_ADMIN)


# ── read ──────────────────────────────────────────────────────────────────────
def list_accounts(conn, me, q=None, role=None, khoa=None) -> list:
    rows = _cur(conn).execute(
        "SELECT id, email, ho_ten, role, created_at, bi_khoa, ly_do_khoa, password_hash IS NOT NULL AS mk, "
        "google_sub IS NOT NULL AS gg, facebook_id IS NOT NULL AS fb, "
        "(SELECT max(created_at) FROM ma_dat_mat_khau m WHERE m.tai_khoan_id = app_user.id AND m.loai = 'moi') AS moi_luc "
        "FROM app_user "
        "WHERE (%(q)s::text IS NULL OR email ILIKE '%%' || %(q)s || '%%' OR ho_ten ILIKE '%%' || %(q)s || '%%') AND (%(r)s::text IS NULL OR role = %(r)s) "
        "AND (%(k)s::boolean IS NULL OR bi_khoa = %(k)s) ORDER BY created_at DESC, id DESC LIMIT %(n)s",
        {"q": (q or "").strip() or None, "r": role, "k": khoa, "n": LIMIT}).fetchall()
    sole = _active_admins(conn)
    sole = sole[0] if len(sole) == 1 else None
    out = []
    for r in rows:
        reason = SELF if me and r["id"] == me["id"] else LAST_ADMIN if r["id"] == sole else None
        out.append({"id": r["id"], "email": r["email"], "ho_ten": r["ho_ten"], "role": r["role"], "created_at": r["created_at"],
                    "dang_nhap": [m for m, on in (("mat_khau", r["mk"]), ("google", r["gg"]), ("facebook", r["fb"])) if on],
                    "bi_khoa": r["bi_khoa"], "ly_do_khoa": r["ly_do_khoa"], "la_toi": bool(me and r["id"] == me["id"]),
                    "doi_vai_tro_duoc": reason is None, "khoa_duoc": reason is None and not r["bi_khoa"],
                    "ly_do_khong": reason, "moi_luc": r["moi_luc"],
                    # invited, and no password / Google / Facebook yet (account-invites-reset)
                    "chua_kich_hoat": bool(r["moi_luc"]) and not (r["mk"] or r["gg"] or r["fb"])})
    return out


def recent(conn) -> list:
    return _cur(conn).execute(
        "SELECT n.id, n.hanh_dong, n.truoc, n.sau, n.created_at, a.email AS boi, t.email AS tai_khoan "
        "FROM nhat_ky_tai_khoan n LEFT JOIN app_user a ON a.id = n.nguoi_dung_id LEFT JOIN app_user t ON t.id = n.tai_khoan_id "
        "ORDER BY n.created_at DESC, n.id DESC LIMIT %s", (LOG_SHOWN,)).fetchall()


# ── write ─────────────────────────────────────────────────────────────────────
def change_role(conn, admin, user_id, role) -> dict:
    if role not in ROLES:
        raise Invalid(f"role must be one of {ROLES}")
    t = _target(conn, user_id)
    if t["role"] == role:
        return {"id": t["id"], "email": t["email"], "role": role}
    _guard(conn, admin, t, removes_admin=t["role"] == "admin")
    conn.execute("UPDATE app_user SET role = %s WHERE id = %s", (role, user_id))
    _log(conn, admin, user_id, "doi_vai_tro", {"role": t["role"]}, {"role": role})
    return {"id": t["id"], "email": t["email"], "role": role}


def lock(conn, admin, user_id, reason: str) -> dict:
    reason = " ".join((reason or "").split())
    if not 3 <= len(reason) <= 300:
        raise Invalid("lý do khoá cần 3 đến 300 ký tự")
    t = _target(conn, user_id)
    if t["bi_khoa"]:
        raise Conflict("tài khoản đã bị khoá")
    _guard(conn, admin, t, removes_admin=True)
    conn.execute("UPDATE app_user SET bi_khoa = true, ly_do_khoa = %s, phien_tu = clock_timestamp() WHERE id = %s",
                 (reason, user_id))
    _log(conn, admin, user_id, "khoa", {"bi_khoa": False}, {"bi_khoa": True, "ly_do": reason})
    return {"id": t["id"], "email": t["email"], "bi_khoa": True, "ly_do_khoa": reason}


def unlock(conn, admin, user_id) -> dict:
    t = _target(conn, user_id)
    if not t["bi_khoa"]:
        raise Conflict("tài khoản không bị khoá")
    if admin and t["id"] == admin["id"]:  # unreachable in practice (a locked admin cannot sign in), kept for symmetry
        raise Conflict(SELF)
    conn.execute("UPDATE app_user SET bi_khoa = false, ly_do_khoa = NULL WHERE id = %s", (user_id,))  # phien_tu stays
    _log(conn, admin, user_id, "mo_khoa", {"bi_khoa": True, "ly_do": t["ly_do_khoa"]}, {"bi_khoa": False})
    return {"id": t["id"], "email": t["email"], "bi_khoa": False}


# ── invitations (change account-invites-reset; seq-19 b1-8) ───────────────────
CANCELLED = "Huỷ lời mời"


def _pending(conn, user_id) -> dict:
    t = _cur(conn).execute(
        "SELECT id, email, role, bi_khoa, password_hash IS NULL AND google_sub IS NULL AND facebook_id IS NULL AS chua, "
        "EXISTS (SELECT 1 FROM ma_dat_mat_khau m WHERE m.tai_khoan_id = app_user.id AND m.loai = 'moi') AS da_moi "
        "FROM app_user WHERE id = %s FOR UPDATE", (user_id,)).fetchone()
    if not t:
        raise NotFound("user not found")
    if not (t["chua"] and t["da_moi"]):
        raise Conflict("tài khoản đã kích hoạt hoặc không được mời")
    return t


def invite(conn, admin, email: str, role: str, ho_ten: str | None = None) -> tuple[dict, str]:
    """Create the account with its role and no password, and an invitation link code (seq-19 b5-7)."""
    email = (email or "").strip().lower()
    if role not in ROLES:
        raise Invalid(f"role must be one of {ROLES}")
    if _cur(conn).execute("SELECT 1 FROM app_user WHERE email = %s", (email,)).fetchone():
        raise Conflict("Email này đã có tài khoản; đổi vai trò ở danh sách bên dưới.")
    user = _cur(conn).execute("INSERT INTO app_user (email, role, ho_ten) VALUES (%s, %s, %s) RETURNING id, email, role, ho_ten",
                              (email, role, ho_ten)).fetchone()
    code = password_links.issue(conn, user["id"], "moi", admin["id"] if admin else None)
    _log(conn, admin, user["id"], "moi", None, {"role": role})
    return user, code


def resend(conn, admin, user_id) -> tuple[dict, str]:
    t = _pending(conn, user_id)
    if t["bi_khoa"]:  # a cancelled invitation is reopened by unlocking first
        raise Conflict("Lời mời đã bị huỷ; mở khoá tài khoản rồi gửi lại.")
    code = password_links.issue(conn, user_id, "moi", admin["id"] if admin else None)
    _log(conn, admin, user_id, "gui_lai_moi", None, {"role": t["role"]})
    return {"id": t["id"], "email": t["email"], "role": t["role"]}, code


def cancel(conn, admin, user_id) -> dict:
    t = _pending(conn, user_id)
    password_links.void(conn, user_id)
    conn.execute("UPDATE app_user SET bi_khoa = true, ly_do_khoa = %s, phien_tu = clock_timestamp() WHERE id = %s",
                 (CANCELLED, user_id))
    _log(conn, admin, user_id, "huy_moi", {"bi_khoa": t["bi_khoa"]}, {"bi_khoa": True, "ly_do": CANCELLED})
    return {"id": t["id"], "email": t["email"], "role": t["role"], "bi_khoa": True, "ly_do_khoa": CANCELLED}
