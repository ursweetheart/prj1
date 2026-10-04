"""Needs Postgres up + ingested data (see test_search.py). Reads run as admin: the data is still unpublished."""
import psycopg

from conftest import client
from pipeline.store import DSN


def test_list_filter_and_get(as_role):
    h = as_role("admin")
    rows = client.get("/spaces", params={"space_type": "phong_khach", "limit": 3}, headers=h).json()
    assert rows and all(r["space_type"] == "phong_khach" for r in rows)
    assert client.get(f"/spaces/{rows[0]['id']}", headers=h).json()["relative_path"] == rows[0]["relative_path"]
    assert client.get("/spaces/0", headers=h).status_code == 404


def test_similar_same_type_excludes_self(as_role):
    h = as_role("admin")
    sid = client.get("/spaces", params={"space_type": "phong_ngu_master", "limit": 1}, headers=h).json()[0]["id"]
    hits = client.get(f"/spaces/{sid}/similar", headers=h).json()
    assert hits and all(x["space_type"] == "phong_ngu_master" and x["id"] != sid for x in hits)


def test_text_search_vietnamese(as_role):
    h = as_role("admin")
    hits = client.get("/search", params={"q": "phòng ngủ ấm áp tông gỗ", "space_type": "phong_ngu_master"}, headers=h).json()
    assert hits and all(x["space_type"] == "phong_ngu_master" for x in hits)
    assert client.get("/search", params={"q": "x", "space_type": "bogus"}, headers=h).status_code == 422


def test_review_flow_and_validation(as_role):
    h = as_role("lead_architect")
    sid = client.get("/spaces", params={"review_status": "draft", "limit": 1}, headers=h).json()[0]["id"]
    orig = client.get(f"/spaces/{sid}", headers=h).json()["design_style"]
    try:
        r = client.patch(f"/spaces/{sid}", json={"advance": True, "design_style": "Japandi"}, headers=h).json()
        assert r["review_status"] == "in_review" and r["design_style"] == "Japandi"
        assert client.patch(f"/spaces/{sid}", json={"design_style": "nope"}, headers=h).status_code == 422
    finally:  # leave the data as found
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM review_log WHERE space_id=%s", (sid,))
            c.execute("UPDATE space SET review_status='draft', design_style=%s WHERE id=%s", (orig, sid))


def test_ingest_rejects_non_image(as_role):
    r = client.post("/spaces/ingest", files={"file": ("notes.txt", b"hello", "text/plain")}, headers=as_role("architect"))
    assert r.status_code == 415


def test_review_cannot_pass_final_state(as_role):
    h = as_role("lead_architect")
    sid = client.get("/spaces", params={"review_status": "draft", "limit": 1}, headers=h).json()[0]["id"]
    try:
        for expected in ("in_review", "approved", "published"):
            assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=h).json()["review_status"] == expected
        assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=h).status_code == 409
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM review_log WHERE space_id=%s", (sid,))
            c.execute("UPDATE space SET review_status='draft' WHERE id=%s", (sid,))
