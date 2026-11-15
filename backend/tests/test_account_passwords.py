"""Invitations and password links (change account-invites-reset). Mail is collected, never sent; accounts are
throw-away @example.com and removed afterwards."""
import logging
import re
import time
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import notify, password_links as pl
from pipeline.store import DSN


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def mail(monkeypatch):
    sent = []
    monkeypatch.setenv("D3_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(notify, "_send", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


@pytest.fixture
def emails():
    made = []

    def new():
        e = f"pw-{uuid.uuid4().hex[:8]}@example.com"
        made.append(e)
        return e
    yield new
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM app_user WHERE email = ANY(%s)", (made,))


def _user(email, password="correct-horse-battery", **cols):
    from auth import _hasher
    with psycopg.connect(DSN) as c:
        uid = c.execute("INSERT INTO app_user (email, password_hash) VALUES (%s, %s) RETURNING id",
                        (email, _hasher.hash(password) if password else None)).fetchone()[0]
        for k, v in cols.items():
            c.execute(f"UPDATE app_user SET {k} = %s WHERE id = %s", (v, uid))
    return uid


def _code(text):
    return re.search(r"#ma=([A-Za-z0-9_-]+)", text).group(1)


def _login(email, pw):
    return client.post("/auth/login", data={"username": email, "password": pw})


# ── 1.2 links ───────────────────────────────────────────────────────────────────
def test_expiry_single_use_and_replacement(emails):
    uid = _user(emails())
    with psycopg.connect(DSN) as c:
        first = pl.issue(c, uid, "dat_lai")
        second = pl.issue(c, uid, "dat_lai")
        with pytest.raises(pl.LinkError) as e:
            pl.check(c, first)
        assert e.value.reason == "da_huy"
        pl.use(c, second, "x")
        with pytest.raises(pl.LinkError) as e:
            pl.check(c, second)
        assert e.value.reason == "da_dung"
        late = pl.issue(c, uid, "dat_lai")
        c.execute("UPDATE ma_dat_mat_khau SET het_han = now() - interval '1 second' WHERE ma_bam = %s", (pl._hash(late),))
        with pytest.raises(pl.LinkError) as e:
            pl.check(c, late)
        assert e.value.reason == "het_han"
    ttl = dict(_q("SELECT loai, round(extract(epoch FROM het_han - created_at) / 3600) FROM ma_dat_mat_khau "
                  "WHERE tai_khoan_id = %s GROUP BY loai, het_han, created_at", uid))
    assert ttl == {"dat_lai": 1}
    with psycopg.connect(DSN) as c:
        inv = pl.issue(c, uid, "moi")
    hours = _q("SELECT round(extract(epoch FROM het_han - created_at) / 3600) FROM ma_dat_mat_khau WHERE ma_bam = %s",
               pl._hash(inv))[0][0]
    assert hours == 72


def test_only_hash_stored_and_locked_refused(emails):
    uid = _user(emails(), bi_khoa=True)
    with psycopg.connect(DSN) as c:
        code = pl.issue(c, uid, "dat_lai")
        with pytest.raises(pl.LinkError) as e:
            pl.check(c, code)
        assert e.value.reason == "khoa"
    dump = str(_q("SELECT * FROM ma_dat_mat_khau WHERE tai_khoan_id = %s", uid))
    assert code not in dump and pl._hash(code) in dump


def test_reset_ends_old_sessions(emails, mail):
    email = emails()
    _user(email)
    old = _login(email, "correct-horse-battery").json()["access_token"]
    assert client.post("/auth/forgot", json={"email": email}).status_code == 202
    code = _code(mail[-1][2])
    time.sleep(0.01)
    r = client.post("/auth/set-password", json={"ma": code, "mat_khau": "new-password-123"})
    assert r.status_code == 200
    new = r.json()["access_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {new}"}).status_code == 200
    assert _login(email, "new-password-123").status_code == 200 and _login(email, "correct-horse-battery").status_code == 401


# ── 1.3 invitations ─────────────────────────────────────────────────────────────
def _list(h, email):
    return next(u for u in client.get("/users", params={"q": email}, headers=h).json()["items"] if u["email"] == email)


def test_invite_with_and_without_email(emails, as_role, mail, monkeypatch):
    admin = as_role("admin")
    email = emails()
    r = client.post("/users/invite", json={"email": email, "role": "architect"}, headers=admin)
    assert r.status_code == 201 and r.json()["gui_email"] is True and "link" not in r.json()
    assert mail[-1][0] == email and "Kiến trúc sư" in mail[-1][2] and "#ma=" in mail[-1][2]
    (role, pw), = _q("SELECT role, password_hash FROM app_user WHERE email = %s", email)
    assert role == "architect" and pw is None
    row = _list(admin, email)
    assert row["chua_kich_hoat"] and row["moi_luc"]
    assert client.post("/users/invite", json={"email": email.upper(), "role": "sales"}, headers=admin).status_code == 409

    monkeypatch.delenv("D3_SMTP_HOST")
    other = emails()
    r = client.post("/users/invite", json={"email": other, "role": "sales"}, headers=admin).json()
    assert r["gui_email"] is False and "#ma=" in r["link"]


def test_invite_roles(as_role, emails):
    for role in ("lead_architect", "sales", "visitor"):
        assert client.post("/users/invite", json={"email": emails(), "role": "architect"}, headers=as_role(role)).status_code == 403
    assert client.post("/users/invite", json={"email": emails(), "role": "architect"}).status_code == 401
    assert client.post("/users/invite", json={"email": emails(), "role": "boss"}, headers=as_role("admin")).status_code == 422


def test_resend_cancel_and_log(emails, as_role, mail):
    admin = as_role("admin")
    email = emails()
    uid = client.post("/users/invite", json={"email": email, "role": "content"}, headers=admin).json()["user"]["id"]
    first = _code(mail[-1][2])
    assert client.post(f"/users/{uid}/invite/resend", headers=admin).status_code == 200
    second = _code(mail[-1][2])
    assert client.post("/auth/link-info", json={"ma": first}).status_code == 410
    assert client.post("/auth/link-info", json={"ma": second}).json()["loai"] == "moi"
    assert client.post(f"/users/{uid}/invite/cancel", headers=admin).json()["user"]["ly_do_khoa"] == "Huỷ lời mời"
    gone = client.post("/auth/link-info", json={"ma": second})
    assert gone.status_code == 410 and gone.json()["detail"]["ly_do"] == "da_huy"
    actions = [a for (a,) in _q("SELECT hanh_dong FROM nhat_ky_tai_khoan WHERE tai_khoan_id = %s ORDER BY id", uid)]
    assert actions == ["moi", "gui_lai_moi", "huy_moi"]
    active = emails()
    aid = _user(active)
    assert client.post(f"/users/{aid}/invite/resend", headers=admin).status_code == 409
    assert client.post(f"/users/{aid}/invite/cancel", headers=admin).status_code == 409


# ── 1.4 public endpoints ────────────────────────────────────────────────────────
def test_forgot_reveals_nothing(emails, mail):
    real, locked, unknown = emails(), emails(), emails()
    _user(real); _user(locked, bi_khoa=True)
    fb = f"facebook-{uuid.uuid4().hex[:6]}@facebook.invalid"
    _user(fb, password=None)
    try:
        answers = [client.post("/auth/forgot", json={"email": e}) for e in (real, unknown, locked)]
        assert len({(a.status_code, a.text) for a in answers}) == 1 and answers[0].status_code == 202
        # a placeholder address is rejected as an email before any lookup, whether or not an account exists
        assert client.post("/auth/forgot", json={"email": fb}).status_code == 422
        assert [m[0] for m in mail] == [real]
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM app_user WHERE email = %s", (fb,))


def test_forgot_rate_limit(emails):
    e = emails()
    codes = [client.post("/auth/forgot", json={"email": e}).status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]


def test_without_smtp_reset_link_logged(emails, monkeypatch, caplog):
    monkeypatch.delenv("D3_SMTP_HOST", raising=False)
    e = emails()
    uid = _user(e)
    with caplog.at_level(logging.INFO, logger="d3.auth"):
        client.post("/auth/forgot", json={"email": e})
    assert f"account #{uid}" in caplog.text and "#ma=" in caplog.text


def test_set_password_from_invitation(emails, as_role, mail):
    admin = as_role("admin")
    email = emails()
    client.post("/users/invite", json={"email": email, "role": "architect"}, headers=admin)
    code = _code(mail[-1][2])
    info = client.post("/auth/link-info", json={"ma": code}).json()
    assert info == {"loai": "moi", "email_an": email[0] + "***@example.com"}
    assert client.post("/auth/set-password", json={"ma": code, "mat_khau": "short7!"}).status_code == 422
    r = client.post("/auth/set-password", json={"ma": code, "mat_khau": "a-good-password"})
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "architect" and me["email"] == email
    assert not _list(admin, email)["chua_kich_hoat"]
    again = client.post("/auth/set-password", json={"ma": code, "mat_khau": "another-password"})
    assert again.status_code == 410 and again.json()["detail"]["ly_do"] == "da_dung"
    assert client.post("/auth/link-info", json={"ma": "nonsense"}).json()["detail"]["ly_do"] == "khong_hop_le"
