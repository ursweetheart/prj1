import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app
from pipeline.store import DSN

client = TestClient(app)


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
