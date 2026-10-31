"""Accounts, roles, visibility and audit log (task group 6). Needs Postgres + ingested data."""
import psycopg

import auth
from conftest import client
from pipeline.store import DSN


def _draft_id(h):
    return client.get("/spaces", params={"review_status": "draft", "limit": 1}, headers=h).json()[0]["id"]


def _reset(sid):
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM review_log WHERE space_id=%s", (sid,))
        c.execute("UPDATE space SET review_status='draft' WHERE id=%s", (sid,))


def test_register_login_me_and_bad_credentials():
    body = {"email": "Reg-Test@Example.com", "password": "long-enough-pw"}
    try:
        r = client.post("/auth/register", json=body)
        assert r.status_code == 201 and r.json()["role"] == "visitor" and r.json()["email"] == "reg-test@example.com"
        assert client.post("/auth/register", json=body).status_code == 409  # duplicate, case-insensitive
        assert client.post("/auth/register", json={**body, "email": "x@example.com", "password": "short"}).status_code == 422
        tok = client.post("/auth/login", data={"username": body["email"], "password": body["password"]}).json()["access_token"]
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["email"] == "reg-test@example.com"
        assert client.post("/auth/login", data={"username": body["email"], "password": "wrong-password"}).status_code == 401
        assert client.post("/auth/login", data={"username": "nobody@example.com", "password": "whatever-pw"}).status_code == 401
        assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
        assert client.get("/auth/me").status_code == 401
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM app_user WHERE email='reg-test@example.com'")


def test_passwords_are_hashed():
    with psycopg.connect(DSN) as c:
        client.post("/auth/register", json={"email": "hash-test@example.com", "password": "plain-secret-1"})
        try:
            (h,) = c.execute("SELECT password_hash FROM app_user WHERE email='hash-test@example.com'").fetchone()
            assert "plain-secret-1" not in h and h.startswith("$argon2")
        finally:
            c.execute("DELETE FROM app_user WHERE email='hash-test@example.com'")


def test_anonymous_and_visitor_see_only_published(as_role):
    admin = as_role("admin")
    sid = _draft_id(admin)
    try:
        for h in ({}, as_role("visitor"), as_role("sales")):
            assert client.get(f"/spaces/{sid}", headers=h).status_code == 404
            assert client.get(f"/spaces/{sid}/similar", headers=h).status_code == 404
            listed = client.get("/spaces", params={"limit": 200}, headers=h).json()
            assert all(r["review_status"] == "published" for r in listed)
            assert client.get("/spaces", params={"review_status": "draft"}, headers=h).json() == []
            hits = client.get("/search", params={"q": "phòng khách", "k": 24}, headers=h).json()
            assert sid not in [x["id"] for x in hits]
        assert client.get(f"/spaces/{sid}", headers=as_role("architect")).status_code == 200
        for _ in range(4):  # draft -> in_review -> approved -> cleared -> published
            client.patch(f"/spaces/{sid}", json={"advance": True, "rights_confirmed": True}, headers=admin)
        assert client.get(f"/spaces/{sid}").status_code == 200  # published -> public
    finally:
        _reset(sid)


def test_write_endpoints_by_role(as_role):
    sid = _draft_id(as_role("admin"))
    png = {"file": ("a.png", b"x", "image/png")}
    try:
        # ingest + edit: anonymous 401, non-architect roles 403
        assert client.post("/spaces/ingest", files=png).status_code == 401
        assert client.patch(f"/spaces/{sid}", json={"advance": True}).status_code == 401
        for role in ("visitor", "content", "sales"):
            h = as_role(role)
            assert client.post("/spaces/ingest", files=png, headers=h).status_code == 403
            assert client.patch(f"/spaces/{sid}", json={"design_style": "Japandi"}, headers=h).status_code == 403
        # architect: may edit and send draft -> in_review, may not approve
        arch = as_role("architect")
        assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=arch).json()["review_status"] == "in_review"
        assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=arch).status_code == 403
        # lead architect approves, clears (with the rights confirmation) and publishes
        lead = as_role("lead_architect")
        assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=lead).json()["review_status"] == "approved"
        assert client.patch(f"/spaces/{sid}", json={"advance": True, "rights_confirmed": True}, headers=lead).json()["review_status"] == "cleared"
        assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=lead).json()["review_status"] == "published"
    finally:
        _reset(sid)


def test_only_admin_changes_roles(as_role):
    admin = as_role("admin")
    me = client.get("/auth/me", headers=as_role("visitor")).json()
    assert client.patch(f"/users/{me['id']}/role", json={"role": "admin"}, headers=as_role("lead_architect")).status_code == 403
    assert client.patch(f"/users/{me['id']}/role", json={"role": "root"}, headers=admin).status_code == 422
    assert client.patch(f"/users/{me['id']}/role", json={"role": "architect"}, headers=admin).json()["role"] == "architect"
    assert client.patch("/users/0/role", json={"role": "architect"}, headers=admin).status_code == 404


def test_audit_log_records_who_and_what(as_role):
    arch = as_role("architect")
    uid = client.get("/auth/me", headers=arch).json()["id"]
    sid = _draft_id(arch)
    orig = client.get(f"/spaces/{sid}", headers=arch).json()["design_style"]
    style = "Luxury" if orig == "Japandi" else "Japandi"  # an edit that changes nothing is not logged
    try:
        client.patch(f"/spaces/{sid}", json={"advance": True, "design_style": style}, headers=arch)
        with psycopg.connect(DSN) as c:
            rows = c.execute("SELECT action, detail FROM review_log WHERE space_id=%s AND user_id=%s ORDER BY id", (sid, uid)).fetchall()
        assert [r[0] for r in rows] == ["edit", "advance"]
        assert rows[0][1]["to"]["design_style"] == style and rows[1][1] == {"from": "draft", "to": "in_review"}
    finally:
        _reset(sid)
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE space SET design_style=%s WHERE id=%s", (orig, sid))


def test_google_sign_in_linking_and_config():
    assert client.get("/auth/google/login").status_code == 501  # not configured in tests
    email = "google-test@example.com"
    with psycopg.connect(DSN) as c:
        try:
            client.post("/auth/register", json={"email": email, "password": "password-before"})
            uid = auth.upsert_google_user("sub-123", email)  # same verified email -> linked, not duplicated
            assert auth.upsert_google_user("sub-123", "renamed@example.com") == uid  # sub wins over email
            assert c.execute("SELECT password_hash FROM app_user WHERE id=%s", (uid,)).fetchone()[0] is None
            assert client.post("/auth/login", data={"username": email, "password": "password-before"}).status_code == 401
            new = auth.upsert_google_user("sub-456", "brand-new@example.com")
            assert c.execute("SELECT role FROM app_user WHERE id=%s", (new,)).fetchone()[0] == "visitor"
        finally:
            c.execute("DELETE FROM app_user WHERE google_sub IN ('sub-123','sub-456')")


def test_facebook_sign_in_never_links_by_email(monkeypatch):
    assert client.get("/auth/facebook/login").status_code == 501  # not configured in tests
    email = "victim@example.com"
    with psycopg.connect(DSN) as c:
        try:
            victim = client.post("/auth/register", json={"email": email, "password": "password-before"}).json()["id"]
            uid = auth.upsert_facebook_user("fb-1")
            assert uid != victim and auth.upsert_facebook_user("fb-1") == uid  # stable per Facebook id
            assert c.execute("SELECT role FROM app_user WHERE id=%s", (uid,)).fetchone()[0] == "visitor"
            assert client.post("/auth/login", data={"username": email, "password": "password-before"}).status_code == 200
        finally:
            c.execute("DELETE FROM app_user WHERE facebook_id = 'fb-1' OR email = %s", (email,))


def test_oauth_returns_to_the_site_when_frontend_url_is_set(monkeypatch):
    assert auth._signed_in(1)["token_type"] == "bearer"
    monkeypatch.setenv("D3_FRONTEND_URL", "http://localhost:5173/prj1/")
    r = auth._signed_in(1)
    assert r.status_code == 307 and r.headers["location"].startswith("http://localhost:5173/prj1/#token=")


def test_refresh_issues_a_new_token_only_for_a_valid_one(as_role):
    assert client.post("/auth/refresh").status_code == 401
    assert client.post("/auth/refresh", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    r = client.post("/auth/refresh", headers=as_role("visitor"))
    assert r.status_code == 200
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}).status_code == 200
