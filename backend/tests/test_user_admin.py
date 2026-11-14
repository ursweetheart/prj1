"""Account admin (change user-admin): lock / revoke, guards, endpoints. Throw-away @example.com accounts only.
Guards that depend on how many admins exist run inside a transaction that is rolled back."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import psycopg
import pytest
from psycopg.rows import dict_row

import auth
from conftest import client
from pipeline import accounts
from pipeline.store import DSN

PW = "correct-horse-battery"


@pytest.fixture
def people():
    """people(role) -> (id, email, headers) for a fresh account; all removed afterwards."""
    made = []

    def make(role="visitor"):
        email = f"ua-{uuid.uuid4().hex[:8]}@example.com"
        uid = client.post("/auth/register", json={"email": email, "password": PW}).json()["id"]
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE app_user SET role=%s WHERE id=%s", (role, uid))
        made.append(uid)
        tok = client.post("/auth/login", data={"username": email, "password": PW}).json()["access_token"]
        return uid, email, {"Authorization": f"Bearer {tok}"}

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM nhat_ky_tai_khoan WHERE tai_khoan_id = ANY(%(m)s) OR nguoi_dung_id = ANY(%(m)s)", {"m": made})
        c.execute("DELETE FROM app_user WHERE id = ANY(%s)", (made,))


def _login(email, pw=PW):
    return client.post("/auth/login", data={"username": email, "password": pw})


# ── 1.1 sign-in and sessions ───────────────────────────────────────────────────
def test_lock_ends_sessions_and_blocks_sign_in(people):
    _, _, admin = people("admin")
    uid, email, h = people("architect")
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.post(f"/users/{uid}/lock", json={"ly_do": "Nghỉ việc"}, headers=admin).status_code == 200
    r = client.get("/auth/me", headers=h)
    assert r.status_code == 401 and "khoá" in r.json()["detail"]
    assert client.post("/auth/refresh", headers=h).status_code == 401
    r = _login(email)
    assert r.status_code == 403 and r.json()["detail"] == auth.LOCKED
    assert _login(email, "wrong-password-123").status_code == 401  # a wrong password reveals nothing about the lock
    assert client.post(f"/users/{uid}/unlock", headers=admin).status_code == 200
    assert client.get("/auth/me", headers=h).status_code == 401           # the pre-lock token stays dead
    fresh = {"Authorization": "Bearer " + _login(email).json()["access_token"]}
    assert client.get("/auth/me", headers=fresh).json()["id"] == uid


def test_token_without_iat_works_until_a_lock(people):
    _, _, admin = people("admin")
    uid, _, _ = people("visitor")
    old = jwt.encode({"sub": str(uid), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, auth.SECRET, algorithm="HS256")
    h = {"Authorization": f"Bearer {old}"}
    assert client.get("/auth/me", headers=h).status_code == 200
    client.post(f"/users/{uid}/lock", json={"ly_do": "thử"}, headers=admin)
    client.post(f"/users/{uid}/unlock", headers=admin)
    assert client.get("/auth/me", headers=h).status_code == 401


def test_oauth_sign_in_refuses_locked(people, monkeypatch):
    _, _, admin = people("admin")
    uid, _, _ = people("visitor")
    client.post(f"/users/{uid}/lock", json={"ly_do": "thử OAuth"}, headers=admin)
    monkeypatch.delenv("D3_FRONTEND_URL", raising=False)
    with pytest.raises(Exception) as e:
        auth._signed_in(uid)
    assert getattr(e.value, "status_code", None) == 403
    monkeypatch.setenv("D3_FRONTEND_URL", "http://site.test/prj1")
    r = auth._signed_in(uid)
    assert r.status_code in (302, 307) and r.headers["location"] == "http://site.test/prj1/dang-nhap#loi=tai_khoan_bi_khoa"


def test_tokens_carry_iat():
    claims = jwt.decode(auth.make_token(1), auth.SECRET, algorithms=["HS256"])
    assert abs(claims["iat"] - datetime.now(timezone.utc).timestamp()) < 5


# ── 1.2 guards and list ────────────────────────────────────────────────────────
def test_self_guard(people):
    aid, _, admin = people("admin")
    for call in (lambda: client.patch(f"/users/{aid}/role", json={"role": "lead_architect"}, headers=admin),
                 lambda: client.post(f"/users/{aid}/lock", json={"ly_do": "tự khoá"}, headers=admin)):
        r = call()
        assert r.status_code == 409 and r.json()["detail"] == accounts.SELF
    assert client.get("/auth/me", headers=admin).json()["role"] == "admin"


def test_last_active_admin_guard(people):
    a, _, _ = people("admin")
    b, _, _ = people("admin")
    me = {"id": b, "role": "admin"}
    with psycopg.connect(DSN, row_factory=dict_row) as c:
        try:
            # make `a` the only active admin: lock every other admin inside this transaction (rolled back below)
            c.execute("UPDATE app_user SET bi_khoa = true WHERE role = 'admin' AND id <> %s", (a,))
            with pytest.raises(accounts.Conflict, match="ít nhất một"):
                accounts.change_role(c, me, a, "visitor")
            with pytest.raises(accounts.Conflict, match="ít nhất một"):
                accounts.lock(c, me, a, "thử khoá")
            row = next(r for r in accounts.list_accounts(c, me) if r["id"] == a)
            assert not row["khoa_duoc"] and not row["doi_vai_tro_duoc"] and row["ly_do_khong"] == accounts.LAST_ADMIN
            c.execute("UPDATE app_user SET bi_khoa = false WHERE id = %s", (b,))  # two active admins: one may go
            assert accounts.change_role(c, me, a, "visitor")["role"] == "visitor"
        finally:
            c.rollback()


def test_list_shape_search_and_log(people):
    aid, aemail, admin = people("admin")
    uid, email, _ = people("visitor")
    r = client.get("/users", params={"q": email[:11]}, headers=admin).json()
    item = next(i for i in r["items"] if i["id"] == uid)
    assert item["dang_nhap"] == ["mat_khau"] and item["bi_khoa"] is False and item["doi_vai_tro_duoc"]
    assert not {"password_hash", "google_sub", "facebook_id", "mk", "gg", "fb"} & set(item)
    mine = next(i for i in client.get("/users", params={"q": aemail}, headers=admin).json()["items"])
    assert mine["la_toi"] and not mine["khoa_duoc"] and mine["ly_do_khong"] == accounts.SELF
    assert all(i["role"] == "admin" for i in client.get("/users", params={"role": "admin"}, headers=admin).json()["items"])
    client.patch(f"/users/{uid}/role", json={"role": "sales"}, headers=admin)
    client.post(f"/users/{uid}/lock", json={"ly_do": "  Nghỉ   việc "}, headers=admin)
    locked = client.get("/users", params={"khoa": "true", "q": email}, headers=admin).json()["items"]
    assert [i["id"] for i in locked] == [uid] and locked[0]["ly_do_khoa"] == "Nghỉ việc"
    client.post(f"/users/{uid}/unlock", headers=admin)
    log = [l for l in client.get("/users", headers=admin).json()["gan_day"] if l["tai_khoan"] == email]
    assert [l["hanh_dong"] for l in log] == ["mo_khoa", "khoa", "doi_vai_tro"]
    assert log[1]["sau"]["ly_do"] == "Nghỉ việc" and log[2]["truoc"] == {"role": "visitor"} and log[0]["boi"] == aemail


# ── 1.3 endpoints ──────────────────────────────────────────────────────────────
def test_roles_and_errors(people):
    _, _, admin = people("admin")
    _, _, lead = people("lead_architect")
    uid, _, visitor = people("visitor")
    assert client.get("/users").status_code == 401
    assert client.get("/users", headers=lead).status_code == 403
    assert client.post(f"/users/{uid}/lock", json={"ly_do": "x"}, headers=lead).status_code == 403
    assert client.patch(f"/users/{uid}/role", json={"role": "root"}, headers=admin).status_code == 422
    assert client.post(f"/users/{uid}/lock", json={"ly_do": " a "}, headers=admin).status_code == 422
    assert client.post("/users/0/lock", json={"ly_do": "không có"}, headers=admin).status_code == 404
    assert client.post(f"/users/{uid}/unlock", headers=admin).status_code == 409   # not locked
    assert client.get("/analytics/overview", params={"days": 7}, headers=visitor).status_code == 403
    assert client.patch(f"/users/{uid}/role", json={"role": "sales"}, headers=admin).json()["role"] == "sales"
    assert client.get("/analytics/overview", params={"days": 7}, headers=visitor).status_code == 200  # same token
