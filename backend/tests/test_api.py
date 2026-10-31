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


def test_tags_follow_columns_and_keep_human_ones(as_role):
    """sync_ai_tags: AI dimensions mirror the space columns; nguon_tao='nguoi' rows survive a re-tag."""
    h = as_role("admin")
    row = client.get("/spaces", params={"space_type": "phong_khach", "limit": 1}, headers=h).json()[0]
    assert row["tags"]["khong_gian"] == ["phong_khach"] and row["tags"]["phong_cach"] == [row["design_style"]]
    other = "Japandi" if row["design_style"] != "Japandi" else "Luxury"
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO space_gia_tri (space_id, gia_tri_id, nguon_tao) SELECT %s, v.id, 'nguoi' FROM gia_tri_phan_loai v "
                  "JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE d.ma_dinh_danh='loai_cong_trinh' AND v.ma_dinh_danh='biet_thu'",
                  (row["id"],))
    try:
        client.patch(f"/spaces/{row['id']}", json={"design_style": other}, headers=h)
        tags = client.get("/spaces", params={"space_type": "phong_khach", "limit": 200}, headers=h).json()
        tags = next(r for r in tags if r["id"] == row["id"])["tags"]
        assert tags["phong_cach"] == [other] and tags["loai_cong_trinh"] == ["biet_thu"]
    finally:
        client.patch(f"/spaces/{row['id']}", json={"design_style": row["design_style"]}, headers=h)
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM space_gia_tri WHERE space_id=%s AND nguon_tao='nguoi'", (row["id"],))


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


def test_project_folder_is_path_safe():
    from api import project_folder
    assert project_folder("Biệt thự Thảo Điền") == "biet_thu_thao_dien"
    assert project_folder("../../etc") == "etc"  # no way out of image_d3
    assert project_folder("  ") == ""             # -> uploads/


def test_ingest_rejects_non_image(as_role):
    r = client.post("/spaces/ingest", files={"file": ("notes.txt", b"hello", "text/plain")}, headers=as_role("architect"))
    assert r.status_code == 415

