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



# ── photo search (search-by-image) ───────────────────────────────────────────
from pathlib import Path

import api

HIT_KEYS = {"relative_path", "space_type", "design_style", "score", "id"}


def _first(where="TRUE"):
    with psycopg.connect(DSN) as c:
        return c.execute(f"SELECT id, relative_path FROM space WHERE {where} ORDER BY id LIMIT 1").fetchone()


def _upload(data, name="photo.jpg", headers=None, **form):
    return client.post("/search/image", files={"file": (name, data)}, data=form, headers=headers)


def test_photo_search_staff_gets_hits_and_nothing_is_stored(as_role):
    h = as_role("architect")
    _, path = _first("space_type='phong_khach'")
    files = lambda: sum(1 for _ in Path("image_d3").rglob("*"))
    with psycopg.connect(DSN) as c:
        before = files(), c.execute("SELECT count(*) FROM space").fetchone()[0]
    r = _upload(Path("image_d3", path).read_bytes(), headers=h)
    assert r.status_code == 200 and r.json() and all(set(x) == HIT_KEYS for x in r.json())
    assert r.json()[0]["score"] >= 0.99  # the photo itself, or a stored duplicate tied with it
    with psycopg.connect(DSN) as c:
        assert (files(), c.execute("SELECT count(*) FROM space").fetchone()[0]) == before


def test_photo_search_visitor_sees_only_published(drafts):
    [sid] = drafts(1)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status='published' WHERE id=%s", (sid,))
        path = c.execute("SELECT relative_path FROM space WHERE id=%s", (sid,)).fetchone()[0]
    hits = _upload(Path("image_d3", path).read_bytes()).json()
    assert sid in [x["id"] for x in hits]
    with psycopg.connect(DSN) as c:
        status = c.execute("SELECT DISTINCT review_status FROM space WHERE id = ANY(%s)", ([x["id"] for x in hits],)).fetchall()
    assert status == [("published",)]


def test_photo_search_rejects_bad_uploads():
    assert _upload(b"%PDF-1.4", "a.pdf").status_code == 415
    assert _upload(b"not an image at all").status_code == 415
    assert _upload(b"0" * (api.MAX_UPLOAD + 1)).status_code == 413
    _, path = _first()
    assert _upload(Path("image_d3", path).read_bytes(), space_type="phong_tam_khong_co").status_code == 422


def test_photo_search_is_rate_limited():
    codes = [_upload(b"x", "a.pdf").status_code for _ in range(11)]  # the limit counts before validation, so cheap requests do
    assert codes[:10] == [415] * 10 and codes[10] == 429
    assert _upload(b"x", "a.pdf").headers["Retry-After"]
