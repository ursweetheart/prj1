"""Needs Postgres up + ingested data (see test_search.py)."""
import psycopg
from fastapi.testclient import TestClient

from api import app
from pipeline.store import DSN

client = TestClient(app)


def test_list_filter_and_get():
    rows = client.get("/spaces", params={"space_type": "phong_khach", "limit": 3}).json()
    assert rows and all(r["space_type"] == "phong_khach" for r in rows)
    assert client.get(f"/spaces/{rows[0]['id']}").json()["relative_path"] == rows[0]["relative_path"]
    assert client.get("/spaces/0").status_code == 404


def test_similar_same_type_excludes_self():
    sid = client.get("/spaces", params={"space_type": "phong_ngu_master", "limit": 1}).json()[0]["id"]
    hits = client.get(f"/spaces/{sid}/similar").json()
    assert hits and all(h["space_type"] == "phong_ngu_master" and h["id"] != sid for h in hits)


def test_text_search_vietnamese():
    hits = client.get("/search", params={"q": "phòng ngủ ấm áp tông gỗ", "space_type": "phong_ngu_master"}).json()
    assert hits and all(h["space_type"] == "phong_ngu_master" for h in hits)
    assert client.get("/search", params={"q": "x", "space_type": "bogus"}).status_code == 422


def test_review_flow_and_validation():
    sid = client.get("/spaces", params={"review_status": "draft", "limit": 1}).json()[0]["id"]
    orig = client.get(f"/spaces/{sid}").json()["design_style"]
    try:
        r = client.patch(f"/spaces/{sid}", json={"advance": True, "design_style": "Japandi"}).json()
        assert r["review_status"] == "in_review" and r["design_style"] == "Japandi"
        assert client.patch(f"/spaces/{sid}", json={"design_style": "nope"}).status_code == 422
    finally:  # leave the data as found
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE space SET review_status='draft', design_style=%s WHERE id=%s", (orig, sid))
