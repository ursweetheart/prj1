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
        taken.extend(rows)
        return [r[0] for r in rows]

    yield take
    with psycopg.connect(DSN) as c:
        for sid, *vals in taken:
            vals[-1] = Jsonb(vals[-1])  # hotspots
            c.execute(f"UPDATE space SET ({COLS}) = (%s,%s,%s,%s,%s,%s,%s) WHERE id=%s", (*vals, sid))
            c.execute("DELETE FROM space_gia_tri WHERE space_id=%s AND nguon_tao='nguoi'", (sid,))
            c.execute("DELETE FROM review_log WHERE space_id=%s", (sid,))
