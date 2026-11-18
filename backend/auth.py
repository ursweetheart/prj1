"""Accounts, JWT bearer tokens, role checks, Google (OIDC) and Facebook (OAuth2) sign-in."""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field

from pipeline import accounts, notify, password_links
from pipeline.store import DSN
from ratelimit import limit

# ponytail: random per-process secret when unset, so tokens die on restart; set D3_JWT_SECRET in production
SECRET = os.getenv("D3_JWT_SECRET") or secrets.token_urlsafe(32)
if not os.getenv("D3_JWT_SECRET"):
    logging.getLogger(__name__).warning("D3_JWT_SECRET is not set: login tokens stop working whenever the server restarts")
TOKEN_TTL = timedelta(minutes=60)
ROLES = accounts.ROLES  # visitor, architect, content, sales, lead_architect, admin
STAFF = {"architect", "lead_architect", "admin"}  # may see drafts, ingest and edit facets
APPROVERS = {"lead_architect", "admin"}  # may approve and publish (QT-01)

_hasher = PasswordHash.recommended()  # argon2id
_DUMMY = _hasher.hash("timing-equaliser")
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
router = APIRouter()


def _conn():
    return psycopg.connect(DSN, row_factory=dict_row)


LOCKED = "Tài khoản đã bị khoá. Liên hệ quản trị viên."


def make_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    # iat (sub-second, as JWT allows): an account's phien_tu (set by a lock) refuses every token issued before it,
    # so even a token from the same second as the lock stays dead after an unlock (user-admin)
    return jwt.encode({"sub": str(user_id), "iat": round(now.timestamp(), 6), "exp": now + TOKEN_TTL}, SECRET, algorithm="HS256")


def optional_user(token: str | None = Depends(oauth2)):
    """The caller, or None for anonymous. The role is read from the DB, so a demotion applies at once."""
    if not token:
        return None
    try:
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        uid, issued = int(claims["sub"]), float(claims.get("iat", 0))  # tokens from before user-admin have no iat
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(401, "invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    with _conn() as c:
        user = c.execute("SELECT id, email, role, bi_khoa, phien_tu, ho_ten FROM app_user WHERE id=%s", (uid,)).fetchone()
    if not user:
        raise HTTPException(401, "unknown user", headers={"WWW-Authenticate": "Bearer"})
    # 401, not 403: the site signs the user out on 401, which is what a lock must do to an open session
    if user.pop("bi_khoa"):
        raise HTTPException(401, LOCKED, headers={"WWW-Authenticate": "Bearer"})
    if (cut := user.pop("phien_tu")) and issued < cut.timestamp():
        raise HTTPException(401, "session ended, please sign in again", headers={"WWW-Authenticate": "Bearer"})
    return user


def require(*roles: str):
    def dep(user=Depends(optional_user)):
        if user is None:
            raise HTTPException(401, "login required", headers={"WWW-Authenticate": "Bearer"})
        if user["role"] not in roles:
            raise HTTPException(403, f"requires role: {', '.join(roles)}")
        return user
    return dep


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    ho_ten: str | None = Field(default=None, max_length=100)  # class-6 NguoiDung (admin-tools), optional


@router.post("/auth/register", status_code=201, dependencies=[Depends(limit("register", 10, 60))])
def register(body: Credentials):
    """Self-service sign-up always yields 'visitor'; staff roles are granted by an admin."""
    try:
        with _conn() as c:
            return c.execute(
                "INSERT INTO app_user (email, password_hash, ho_ten) VALUES (%s, %s, %s) RETURNING id, email, role, ho_ten",
                (body.email.lower(), _hasher.hash(body.password), _name(body.ho_ten))).fetchone()
    except UniqueViolation:
        raise HTTPException(409, "email already registered")


@router.post("/auth/login", dependencies=[Depends(limit("login", 10, 60))])
def login(form: OAuth2PasswordRequestForm = Depends()):
    with _conn() as c:
        u = c.execute("SELECT id, password_hash, bi_khoa FROM app_user WHERE email=%s", (form.username.lower(),)).fetchone()
    ok = _hasher.verify(form.password, (u and u["password_hash"]) or _DUMMY)  # same cost whether or not the user exists
    if not (u and u["password_hash"] and ok):
        raise HTTPException(401, "wrong email or password", headers={"WWW-Authenticate": "Bearer"})
    if u["bi_khoa"]:  # only after the right password: a lock reveals nothing to someone guessing
        raise HTTPException(403, LOCKED)
    return {"access_token": make_token(u["id"]), "token_type": "bearer"}


@router.get("/auth/me")
def me(user=Depends(require(*ROLES))):
    return user


class NameBody(BaseModel):
    ho_ten: str | None = Field(default=None, max_length=100)


def _name(v):
    return " ".join((v or "").split()) or None


@router.patch("/auth/me")
def set_my_name(body: NameBody, user=Depends(require(*ROLES))):
    """The account's own full name (admin-tools); nothing else is changed here."""
    with _conn() as c:
        c.execute("UPDATE app_user SET ho_ten = %s WHERE id = %s", (_name(body.ho_ten), user["id"]))
    return {**user, "ho_ten": _name(body.ho_ten)}


@router.patch("/users/{user_id}")
def set_user_name(user_id: int, body: NameBody, me=Depends(require("admin"))):
    """Admin sets an account's full name (admin-tools)."""
    with _conn() as c:
        row = c.execute("UPDATE app_user SET ho_ten = %s WHERE id = %s RETURNING id, email, role, ho_ten",
                        (_name(body.ho_ten), user_id)).fetchone()
    if not row:
        raise HTTPException(404, "no such account")
    return row


@router.post("/auth/refresh")
def refresh(user=Depends(require(*ROLES))):
    """A fresh token for a still-valid one (sliding session). A deleted user already fails in optional_user."""
    return {"access_token": make_token(user["id"]), "token_type": "bearer"}


class RoleChange(BaseModel):
    role: str


def _accounts(call):
    """One accounts write in a transaction, its errors mapped (user-admin)."""
    try:
        with _conn() as c:
            return call(c)
    except accounts.NotFound as e:
        raise HTTPException(404, str(e))
    except accounts.Conflict as e:
        raise HTTPException(409, str(e))
    except accounts.Invalid as e:
        raise HTTPException(422, str(e))


@router.get("/users")
def list_users(q: str | None = Query(default=None, max_length=200), role: str | None = None, khoa: bool | None = None,
               me=Depends(require("admin"))):
    """Every account (no password hash, Google or Facebook id), whether each control is allowed, and the last changes."""
    with _conn() as c:
        return {"items": accounts.list_accounts(c, me, q, role, khoa), "gan_day": accounts.recent(c)}


@router.patch("/users/{user_id}/role")
def set_role(user_id: int, body: RoleChange, me=Depends(require("admin"))):
    """Applies on the account's next request (the role is read per request); never the caller's own or the last admin's."""
    return _accounts(lambda c: accounts.change_role(c, me, user_id, body.role))


class LockBody(BaseModel):
    ly_do: str = Field(max_length=300)


@router.post("/users/{user_id}/lock")
def lock_user(user_id: int, body: LockBody, me=Depends(require("admin"))):
    """Cannot sign in any more, and every open session ends on its next request (seq-19 b16-19)."""
    return _accounts(lambda c: accounts.lock(c, me, user_id, body.ly_do))


@router.post("/users/{user_id}/unlock")
def unlock_user(user_id: int, me=Depends(require("admin"))):
    return _accounts(lambda c: accounts.unlock(c, me, user_id))


# ---- Invitations and password links (account-invites-reset; UC24, seq-19 b1-14) ----
class InviteBody(BaseModel):
    email: EmailStr
    role: str
    ho_ten: str | None = Field(default=None, max_length=100)


def _invited(me, user, code) -> dict:
    """Email the link; without SMTP give it to the admin to pass on (it is never logged)."""
    link = password_links.link_url(code)
    sent = notify.send_invitation(user["email"], user["role"], link, me.get("ho_ten") or me["email"])
    return {"user": user, "gui_email": sent, **({} if sent else {"link": link})}


@router.post("/users/invite", status_code=201)
def invite_user(body: InviteBody, me=Depends(require("admin"))):
    """Create the account with its role and no password, and send it an invitation link (72 h, single use)."""
    user, code = _accounts(lambda c: accounts.invite(c, me, body.email, body.role, _name(body.ho_ten)))
    return _invited(me, user, code)


@router.post("/users/{user_id}/invite/resend")
def resend_invite(user_id: int, me=Depends(require("admin"))):
    user, code = _accounts(lambda c: accounts.resend(c, me, user_id))
    return _invited(me, user, code)


@router.post("/users/{user_id}/invite/cancel")
def cancel_invite(user_id: int, me=Depends(require("admin"))):
    """Every link stops working and the account is locked with the reason "Huỷ lời mời" (kept for the log)."""
    return {"user": _accounts(lambda c: accounts.cancel(c, me, user_id))}


class ForgotBody(BaseModel):
    email: EmailStr


FORGOT_MSG = "Nếu email này có tài khoản, một liên kết đặt lại mật khẩu đã được gửi. Liên kết dùng được trong 1 giờ."


@router.post("/auth/forgot", status_code=202, dependencies=[Depends(limit("forgot", 5, 600))])
def forgot(body: ForgotBody, tasks: BackgroundTasks):
    """Always the same answer, so it never tells whether an account exists; the mail goes out in the background."""
    email = body.email.lower()
    with _conn() as c:
        u = c.execute("SELECT id FROM app_user WHERE email = %s AND NOT bi_khoa", (email,)).fetchone()
        if u and not email.endswith(".invalid"):
            code = password_links.issue(c, u["id"], "dat_lai")
            tasks.add_task(notify.send_reset, u["id"], email, password_links.link_url(code))
    return {"message": FORGOT_MSG}


class LinkBody(BaseModel):
    ma: str = Field(max_length=200)


class SetPasswordBody(LinkBody):
    mat_khau: str = Field(min_length=8, max_length=128)


def _gone(e: password_links.LinkError):
    return HTTPException(410, {"ly_do": e.reason, "msg": str(e)})


@router.post("/auth/link-info", dependencies=[Depends(limit("link_info", 20, 60))])
def link_info(body: LinkBody):
    """What a link is for (invitation or reset) and whose it is, the email partly hidden; 410 with the reason if unusable."""
    try:
        with _conn() as c:
            link = password_links.check(c, body.ma)
    except password_links.LinkError as e:
        raise _gone(e)
    return {"loai": link["loai"], "email_an": password_links.mask(link["email"])}


@router.post("/auth/set-password", dependencies=[Depends(limit("set_password", 10, 60))])
def set_password(body: SetPasswordBody):
    """Set the password from a link and sign in; a reset ends the account's other sessions."""
    try:
        with _conn() as c:
            link = password_links.use(c, body.ma, _hasher.hash(body.mat_khau))
    except password_links.LinkError as e:
        raise _gone(e)
    return {"access_token": make_token(link["user_id"]), "token_type": "bearer"}


# ---- Google sign-in (authorization-code flow with OIDC) ----
oauth = None
if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        "google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        client_kwargs={"scope": "openid email profile"},
    )


def upsert_google_user(sub: str, email: str) -> int:
    """Find by Google id; else link to the account with that (verified) email; else create a visitor."""
    email = email.lower()
    with _conn() as c:
        u = c.execute("SELECT id FROM app_user WHERE google_sub=%s", (sub,)).fetchone()
        if u:
            return u["id"]
        # Linking drops the password: otherwise someone could pre-register the victim's email, keep the
        # password, and still get in after the real owner signs in with Google.
        u = c.execute("UPDATE app_user SET google_sub=%s, password_hash=NULL WHERE email=%s RETURNING id", (sub, email)).fetchone()
        if u:
            return u["id"]
        return c.execute("INSERT INTO app_user (email, google_sub) VALUES (%s, %s) RETURNING id", (email, sub)).fetchone()["id"]


def _signed_in(user_id: int):
    """JSON for API clients; with D3_FRONTEND_URL set (browser flow) redirect to the site with the token in the fragment.
    A locked account gets no token: back to the sign-in page with the reason, or 403."""
    url = os.getenv("D3_FRONTEND_URL")
    with _conn() as c:
        locked = (c.execute("SELECT bi_khoa FROM app_user WHERE id=%s", (user_id,)).fetchone() or {}).get("bi_khoa")
    if locked:
        if url:
            return RedirectResponse(f"{url.rstrip('/')}/dang-nhap#loi=tai_khoan_bi_khoa")
        raise HTTPException(403, LOCKED)
    token = make_token(user_id)
    if url:
        return RedirectResponse(f"{url}#token={token}")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/google/login")
async def google_login(request: Request):
    if oauth is None:
        raise HTTPException(501, "Google sign-in is not configured (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)")
    return await oauth.google.authorize_redirect(request, str(request.url_for("google_callback")))


@router.get("/auth/google/callback")
async def google_callback(request: Request):
    if oauth is None:
        raise HTTPException(501, "Google sign-in is not configured")
    tok = await oauth.google.authorize_access_token(request)
    info = tok.get("userinfo") or {}
    if not info.get("email_verified"):
        raise HTTPException(403, "Google account email is not verified")
    return _signed_in(upsert_google_user(info["sub"], info["email"]))


# ---- Facebook sign-in (plain OAuth2: no ID token, profile comes from the Graph API) ----
if os.getenv("FACEBOOK_APP_ID") and os.getenv("FACEBOOK_APP_SECRET"):
    from authlib.integrations.starlette_client import OAuth

    oauth = oauth or OAuth()
    oauth.register(
        "facebook",
        client_id=os.environ["FACEBOOK_APP_ID"],
        client_secret=os.environ["FACEBOOK_APP_SECRET"],
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        access_token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        api_base_url="https://graph.facebook.com/v19.0/",
        client_kwargs={"scope": "public_profile"},
    )


def upsert_facebook_user(fb_id: str) -> int:
    """Find by Facebook id, else create a visitor. Never link by email: Facebook does not guarantee a verified one,
    so an attacker could otherwise claim an existing account (or a later Google/password sign-up) by faking it."""
    with _conn() as c:
        u = c.execute("SELECT id FROM app_user WHERE facebook_id=%s", (fb_id,)).fetchone()
        if u:
            return u["id"]
        # placeholder address on a reserved TLD: unique, can never collide with a real account
        return c.execute("INSERT INTO app_user (email, facebook_id) VALUES (%s, %s) RETURNING id",
                         (f"facebook-{fb_id}@facebook.invalid", fb_id)).fetchone()["id"]


@router.get("/auth/facebook/login")
async def facebook_login(request: Request):
    if oauth is None or not hasattr(oauth, "facebook"):
        raise HTTPException(501, "Facebook sign-in is not configured (FACEBOOK_APP_ID / FACEBOOK_APP_SECRET)")
    return await oauth.facebook.authorize_redirect(request, str(request.url_for("facebook_callback")))


@router.get("/auth/facebook/callback")
async def facebook_callback(request: Request):
    if oauth is None or not hasattr(oauth, "facebook"):
        raise HTTPException(501, "Facebook sign-in is not configured")
    tok = await oauth.facebook.authorize_access_token(request)
    resp = await oauth.facebook.get("me", params={"fields": "id"}, token=tok)
    resp.raise_for_status()
    return _signed_in(upsert_facebook_user(resp.json()["id"]))
