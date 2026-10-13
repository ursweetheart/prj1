"""No database needed."""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from ratelimit import limit, reset


def _app(count, seconds=60):
    app = FastAPI()
    app.get("/x", dependencies=[Depends(limit("t", count, seconds))])(lambda: "ok")
    return TestClient(app)


def test_blocks_after_the_limit_with_retry_after():
    reset()
    c = _app(3)
    assert [c.get("/x").status_code for _ in range(4)] == [200, 200, 200, 429]
    assert 1 <= int(c.get("/x").headers["Retry-After"]) <= 60


def test_window_slides(monkeypatch):
    import ratelimit
    reset()
    now = [1000.0]
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: now[0])
    c = _app(1, seconds=10)
    assert c.get("/x").status_code == 200 and c.get("/x").status_code == 429
    now[0] += 11
    assert c.get("/x").status_code == 200


def test_login_and_chat_are_limited():
    from api import app
    client = TestClient(app)
    reset()
    codes = [client.post("/auth/login", data={"username": "nobody@example.com", "password": "wrong-password"}).status_code
             for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    reset()
    bad = [client.post("/chat", json={"message": ""}).status_code for _ in range(21)]  # 422 still counts as a call
    assert bad[20] == 429
