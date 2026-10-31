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
