"""Taxonomy admin endpoints (change: discover-taxonomy-dimensions). Needs the DB + seeded taxonomy."""

import psycopg

from conftest import client
from pipeline.store import DSN


def _cleanup():
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM gia_tri_phan_loai WHERE ma_dinh_danh IN ('test_src', 'test_dst')")


def test_list_has_seeded_dimensions():
    dims = {d["ma_dinh_danh"] for d in client.get("/taxonomy").json()}
    assert {"khong_gian", "phong_cach", "loai_cong_trinh"} <= dims


def test_add_value_requires_login():
    pc = next(d for d in client.get("/taxonomy").json() if d["ma_dinh_danh"] == "phong_cach")
    assert client.post(f"/taxonomy/{pc['id']}/values",
                       json={"ma_dinh_danh": "nope", "ten": "Nope"}).status_code == 401


def test_add_rename_merge(as_role):
    hdr = as_role("lead_architect")
    pc = next(d for d in client.get("/taxonomy").json() if d["ma_dinh_danh"] == "phong_cach")
    try:
        src = client.post(f"/taxonomy/{pc['id']}/values", headers=hdr,
                          json={"ma_dinh_danh": "test_src", "ten": "Src", "tu_dong_nghia": ["src syn"]}).json()
        dst = client.post(f"/taxonomy/{pc['id']}/values", headers=hdr,
                          json={"ma_dinh_danh": "test_dst", "ten": "Dst"}).json()

        renamed = client.patch(f"/taxonomy/values/{src['id']}", headers=hdr, json={"ten": "Src2"})
        assert renamed.status_code == 200 and renamed.json()["ma_dinh_danh"] == "test_src"  # id stable

        merged = client.post(f"/taxonomy/values/{src['id']}/merge", headers=hdr, json={"target_id": dst["id"]})
        assert merged.status_code == 200

        pc2 = next(d for d in client.get("/taxonomy").json() if d["ma_dinh_danh"] == "phong_cach")
        mas = {v["ma_dinh_danh"] for v in pc2["values"]}
        assert "test_src" not in mas and "test_dst" in mas  # source gone, target kept
    finally:
        _cleanup()


# ── discovery review: list / accept / reject (seq-15, discover-taxonomy-dimensions 3.2-3.3, 4.2) ──
import pytest
from psycopg.types.json import Jsonb

import api
from pipeline.discovery import LOW_CONFIDENCE, MARK


@pytest.fixture
def candidate():
    """A promoted proposal; removes it and any dimension accepted from it afterwards."""
    with psycopg.connect(DSN) as c:
        ids = [r[0] for r in c.execute("SELECT id FROM space ORDER BY id LIMIT 3")]
        cid = c.execute("INSERT INTO ung_vien_phan_loai (loai, ten_de_xuat, bang_chung, trang_thai) "
                        "VALUES ('chieu', %s, %s, 'cho_duyet') RETURNING id",
                        (MARK + "Mật độ cây xanh", Jsonb({"mo_ta": "lượng cây", "score": 0.7, "vi_du_space_ids": ids,
                                                          "coverage": 0.5, "distinct": 0.9, "demand": 0.2,
                                                          "nguon": ["image", "chat"]}))).fetchone()[0]
    yield cid, ids
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM chieu_phan_loai WHERE ma_dinh_danh = 'test_mat_do_cay_xanh'")  # cascades values and tags
        c.execute("DELETE FROM ung_vien_phan_loai WHERE id=%s", (cid,))
    api.taxonomy.reload()


def test_candidates_need_a_lead_architect(as_role, candidate):
    cid, _ = candidate
    assert client.get("/taxonomy/candidates").status_code == 401
    assert client.get("/taxonomy/candidates", headers=as_role("architect")).status_code == 403
    assert client.post(f"/taxonomy/candidates/{cid}/accept", headers=as_role("architect"),
                       json={"ten": "x y", "gia_tri": ["a", "b"]}).status_code == 403
    listed = client.get("/taxonomy/candidates", headers=as_role("lead_architect")).json()
    mine = next(r for r in listed["candidates"] if r["id"] == cid)
    assert len(mine["vi_du"]) == 3 and mine["bang_chung"]["nguon"] == ["image", "chat"]


def test_accept_creates_dimension_backtags_and_flags(as_role, candidate, monkeypatch):
    cid, ids = candidate
    monkeypatch.setattr(api.vertex, "available", lambda: True)
    monkeypatch.setattr(api.discovery, "backtag", lambda ten, mo_ta, values: {
        ids[0]: ("nhieu", 0.9), ids[1]: ("it", LOW_CONFIDENCE - 0.1)})  # ids[2] and the rest: skipped by "Gemini"
    hdr = as_role("lead_architect")
    r = client.post(f"/taxonomy/candidates/{cid}/accept", headers=hdr,
                    json={"ten": "Test mật độ cây xanh", "gia_tri": ["Nhiều", "Ít"]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["chieu"] == "test_mat_do_cay_xanh" and body["gia_tri"] == ["nhieu", "it"] and body["gan_nhan"] == 2
    assert ids[1] in body["can_xem_lai"] and ids[2] in body["can_xem_lai"] and ids[0] not in body["can_xem_lai"]
    dim = next(d for d in client.get("/taxonomy").json() if d["ma_dinh_danh"] == "test_mat_do_cay_xanh")
    assert [v["ten"] for v in dim["values"]] == ["Nhiều", "Ít"] and dim["hien_thi_cho_khach"]
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT trang_thai FROM ung_vien_phan_loai WHERE id=%s", (cid,)).fetchone()[0] == "chap_nhan"
        assert c.execute("SELECT count(*) FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id "
                         "WHERE v.chieu_id=%s AND sg.nguon_tao='ai_bo_sung'", (dim["id"],)).fetchone()[0] == 2
    assert client.post(f"/taxonomy/candidates/{cid}/accept", headers=hdr,
                       json={"ten": "Test mật độ cây xanh", "gia_tri": ["Nhiều", "Ít"]}).status_code == 409
    # a human tag replaces the AI back-tag on that dimension
    r = client.put("/spaces/tags", headers=hdr, json={"space_ids": [ids[0]], "dimension": "test_mat_do_cay_xanh", "values": ["it"]})
    assert r.status_code == 200
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT v.ma_dinh_danh, sg.nguon_tao FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id "
                         "WHERE v.chieu_id=%s AND sg.space_id=%s", (dim["id"], ids[0])).fetchall() == [("it", "nguoi")]
        c.execute("DELETE FROM review_log WHERE space_id=%s AND action='tags' AND detail ? 'test_mat_do_cay_xanh'", (ids[0],))


def test_accept_refuses_bad_values_and_writes_nothing_when_gemini_fails(as_role, candidate, monkeypatch):
    cid, _ = candidate
    hdr = as_role("lead_architect")
    assert client.post(f"/taxonomy/candidates/{cid}/accept", headers=hdr,
                       json={"ten": "Test mật độ cây xanh", "gia_tri": ["Nhiều", "nhieu"]}).status_code == 422
    monkeypatch.setattr(api.vertex, "available", lambda: True)

    def boom(*a):
        raise RuntimeError("vertex down")
    monkeypatch.setattr(api.discovery, "backtag", boom)
    with pytest.raises(RuntimeError):
        client.post(f"/taxonomy/candidates/{cid}/accept", headers=hdr, json={"ten": "Test mật độ cây xanh", "gia_tri": ["Nhiều", "Ít"]})
    with psycopg.connect(DSN) as c:
        assert not c.execute("SELECT 1 FROM chieu_phan_loai WHERE ma_dinh_danh='test_mat_do_cay_xanh'").fetchone()
        assert c.execute("SELECT trang_thai FROM ung_vien_phan_loai WHERE id=%s", (cid,)).fetchone()[0] == "cho_duyet"


def test_reject_creates_nothing(as_role, candidate):
    cid, _ = candidate
    hdr = as_role("lead_architect")
    with psycopg.connect(DSN) as c:
        dims = c.execute("SELECT count(*) FROM chieu_phan_loai").fetchone()[0]
    assert client.post(f"/taxonomy/candidates/{cid}/reject", headers=hdr).json()["trang_thai"] == "tu_choi"
    assert client.post(f"/taxonomy/candidates/{cid}/reject", headers=hdr).status_code == 409
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT count(*) FROM chieu_phan_loai").fetchone()[0] == dims
