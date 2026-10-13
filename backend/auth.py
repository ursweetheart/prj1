"""Accounts, JWT bearer tokens, role checks and Google sign-in (OIDC)."""

import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field

from pipeline.store import DSN

# ponytail: random per-process secret when unset, so tokens die on restart; set D3_JWT_SECRET in production
SECRET = os.getenv("D3_JWT_SECRET") or secrets.token_urlsafe(32)
TOKEN_TTL = timedelta(minutes=60)
ROLES = ("visitor", "architect", "content", "sales", "lead_architect", "admin")
STAFF = {"architect", "lead_architect", "admin"}  # may see drafts, ingest and edit facets
APPROVERS = {"lead_architect", "admin"}  # may approve and publish (QT-01)

_hasher = PasswordHash.recommended()  # argon2id
_DUMMY = _hasher.hash("timing-equaliser")
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
router = APIRouter()


def _conn():
    return psycopg.connect(DSN, row_factory=dict_row)


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + TOKEN_TTL
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET, algorithm="HS256")


def optional_user(token: str | None = Depends(oauth2)):
    """The caller, or None for anonymous. The role is read from the DB, so a demotion applies at once."""
    if not token:
        return None
    try:
        uid = int(jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    with _conn() as c:
        user = c.execute("SELECT id, email, role FROM app_user WHERE id=%s", (uid,)).fetchone()
    if not user:
        raise HTTPException(401, "unknown user", headers={"WWW-Authenticate": "Bearer"})
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


@router.post("/auth/register", status_code=201)
def register(body: Credentials):
    """Self-service sign-up always yields 'visitor'; staff roles are granted by an admin."""
    try:
        with _conn() as c:
            return c.execute(
                "INSERT INTO app_user (email, password_hash) VALUES (%s, %s) RETURNING id, email, role",
                (body.email.lower(), _hasher.hash(body.password))).fetchone()
    except UniqueViolation:
        raise HTTPException(409, "email already registered")


@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with _conn() as c:
        u = c.execute("SELECT id, password_hash FROM app_user WHERE email=%s", (form.username.lower(),)).fetchone()
    ok = _hasher.verify(form.password, (u and u["password_hash"]) or _DUMMY)  # same cost whether or not the user exists
    if not (u and u["password_hash"] and ok):
        raise HTTPException(401, "wrong email or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": make_token(u["id"]), "token_type": "bearer"}


@router.get("/auth/me")
def me(user=Depends(require(*ROLES))):
    return user


class RoleChange(BaseModel):
    role: str


@router.patch("/users/{user_id}/role")
def set_role(user_id: int, body: RoleChange, _=Depends(require("admin"))):
    if body.role not in ROLES:
        raise HTTPException(422, f"role must be one of {ROLES}")
    with _conn() as c:
        row = c.execute("UPDATE app_user SET role=%s WHERE id=%s RETURNING id, email, role", (body.role, user_id)).fetchone()
    if not row:
        raise HTTPException(404, "user not found")
    return row


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
    return {"access_token": make_token(upsert_google_user(info["sub"], info["email"])), "token_type": "bearer"}
