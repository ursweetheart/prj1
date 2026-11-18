import uuid

import psycopg
import pytest
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient

import ratelimit
from api import app
from pipeline.store import DSN

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    ratelimit.reset()  # tests share one client IP


@pytest.fixture(autouse=True)
def _always_working_hours(monkeypatch):
    """act-4 (visitor-touchpoints): a chat lead outside working hours is deferred; tests must not depend on the clock.
    test_hours.py sets its own times."""
    monkeypatch.setenv("D3_GIO_LAM_VIEC", "T2-CN 00:00-23:59")


@pytest.fixture(scope="session", autouse=True)
def _drop_test_conversations():
    """Every POST /chat now stores a conversation (chat-history). Tests that chat without cleaning up would leave them
    behind: remove the anonymous ones started while the suite ran. A visitor's consented conversation has a session."""
    with psycopg.connect(DSN) as c:
        started = c.execute("SELECT now()").fetchone()[0]
    yield
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM hoi_thoai WHERE bat_dau >= %s AND phien_id IS NULL", (started,))


@pytest.fixture(scope="session")
def as_role():
    """as_role('admin') -> Authorization headers for a throw-away account with that role."""
    made = []

    def make(role):
        email, pw = f"test-{uuid.uuid4().hex[:8]}@example.com", "correct-horse-battery"
        uid = client.post("/auth/register", json={"email": email, "password": pw}).json()["id"]
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE app_user SET role=%s WHERE id=%s", (role, uid))
        made.append(uid)
        tok = client.post("/auth/login", data={"username": email, "password": pw}).json()["access_token"]
        return {"Authorization": f"Bearer {tok}"}

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM review_log WHERE user_id = ANY(%s)", (made,))
        c.execute("DELETE FROM app_user WHERE id = ANY(%s)", (made,))


COLS = "review_status, space_type, design_style, caption, alt_text, materials, hotspots"


@pytest.fixture
def drafts():
    """drafts(n) -> ids of n draft spaces, restored (columns, human tags, log) after the test."""
    taken = []

    def take(n, where="TRUE"):
        with psycopg.connect(DSN) as c:
            rows = c.execute(f"SELECT id, {COLS} FROM space WHERE review_status='draft' AND {where} ORDER BY id LIMIT %s",
                             (n,)).fetchall()
            ids = [r[0] for r in rows]
            fixes.extend(c.execute("SELECT * FROM nhan_bi_sua WHERE space_id = ANY(%s)", (ids,)).fetchall())
        taken.extend(rows)
        return [r[0] for r in rows]

    fixes = []  # labelling-queue-feedback: corrections of the taken photos, put back as they were
    yield take
    with psycopg.connect(DSN) as c:
        ids = [r[0] for r in taken]
        c.execute("DELETE FROM nhan_bi_sua WHERE space_id = ANY(%s)", (ids,))
        # publishing-workflow: a test that published a draft leaves a publish date, knowledge row and queued task
        c.execute("UPDATE space SET ngay_xuat_ban = NULL WHERE id = ANY(%s)", (ids,))  # every taken photo was a draft
        c.execute("DELETE FROM space_text WHERE space_id = ANY(%s)", (ids,))
        c.execute("DELETE FROM hang_doi_tac_vu WHERE loai = 'nap_tri_thuc' AND (du_lieu->>'space_id')::int = ANY(%s)", (ids,))
        for f in fixes:
            c.execute("INSERT INTO nhan_bi_sua VALUES (%s,%s,%s,%s,%s,%s,%s)", f)
        for sid, *vals in taken:
            vals[-1] = Jsonb(vals[-1])  # hotspots
            c.execute(f"UPDATE space SET ({COLS}) = (%s,%s,%s,%s,%s,%s,%s) WHERE id=%s", (*vals, sid))
            c.execute("DELETE FROM space_gia_tri WHERE space_id=%s AND nguon_tao='nguoi'", (sid,))
            c.execute("DELETE FROM review_log WHERE space_id=%s", (sid,))
