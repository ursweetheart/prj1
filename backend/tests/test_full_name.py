"""admin-tools 5.1: class-6 NguoiDung.ho_ten at sign-up, by invitation, by the admin and by the user."""
import uuid

import psycopg

from conftest import client
from pipeline.store import DSN


def _drop(email):
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM app_user WHERE email=%s", (email,))


def test_sign_up_and_own_name():
    email = f"tfn-{uuid.uuid4().hex[:8]}@example.com"
    try:
        r = client.post("/auth/register", json={"email": email, "password": "correct-horse-battery", "ho_ten": "  Nguyễn  Văn An "})
        assert r.status_code == 201 and r.json()["ho_ten"] == "Nguyễn Văn An"
        tok = client.post("/auth/login", data={"username": email, "password": "correct-horse-battery"}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        assert client.get("/auth/me", headers=h).json()["ho_ten"] == "Nguyễn Văn An"
        assert client.patch("/auth/me", json={"ho_ten": "Trần Thị Bình"}, headers=h).json()["ho_ten"] == "Trần Thị Bình"
        assert client.patch("/auth/me", json={"ho_ten": "x" * 101}, headers=h).status_code == 422
        assert client.patch("/auth/me", json={"ho_ten": "Ai đó"}).status_code == 401
    finally:
        _drop(email)


def test_admin_sets_a_name_and_invites_with_one(as_role):
    admin = as_role("admin")
    target = client.get("/auth/me", headers=as_role("architect")).json()
    r = client.patch(f"/users/{target['id']}", json={"ho_ten": "Lê Kiến Trúc"}, headers=admin)
    assert r.status_code == 200 and r.json()["ho_ten"] == "Lê Kiến Trúc"
    listed = client.get("/users", params={"q": "Lê Kiến Trúc"}, headers=admin).json()
    assert any(u["id"] == target["id"] and u["ho_ten"] == "Lê Kiến Trúc" for u in listed["items"])
    assert client.patch(f"/users/{target['id']}", json={"ho_ten": "x"}, headers=as_role("lead_architect")).status_code == 403
    assert client.patch("/users/0", json={"ho_ten": "x"}, headers=admin).status_code == 404
    email = f"tfn-inv-{uuid.uuid4().hex[:8]}@example.com"
    try:
        r = client.post("/users/invite", json={"email": email, "role": "content", "ho_ten": "Phạm Nội Dung"}, headers=admin)
        assert r.status_code == 201 and r.json()["user"]["ho_ten"] == "Phạm Nội Dung"
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM ma_dat_mat_khau WHERE tai_khoan_id IN (SELECT id FROM app_user WHERE email=%s)", (email,))
            c.execute("DELETE FROM nhat_ky_tai_khoan WHERE tai_khoan_id IN (SELECT id FROM app_user WHERE email=%s)", (email,))
        _drop(email)
