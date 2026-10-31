import importlib

from fastapi.testclient import TestClient


def test_cors_only_for_configured_origins(monkeypatch):
    import api
    monkeypatch.setenv("D3_CORS_ORIGINS", "https://site.example")
    try:
        c = TestClient(importlib.reload(api).app)
        pre = c.options("/chat", headers={"Origin": "https://site.example", "Access-Control-Request-Method": "POST",
                                         "Access-Control-Request-Headers": "authorization,content-type"})
        assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == "https://site.example"
        other = c.options("/chat", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
        assert "access-control-allow-origin" not in other.headers
    finally:
        monkeypatch.delenv("D3_CORS_ORIGINS")
        importlib.reload(api)


def test_no_cors_headers_by_default():
    from api import app
    r = TestClient(app).get("/spaces?limit=1", headers={"Origin": "https://site.example"})
    assert "access-control-allow-origin" not in r.headers
