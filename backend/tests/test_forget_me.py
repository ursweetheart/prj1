"""tracking-pipeline 2.2: act-7 "Xóa dữ liệu của tôi"."""
import uuid

import psycopg

from conftest import client
from pipeline.store import DSN


def _session(pid, dev, n):
    sid = None
    with psycopg.connect(DSN) as c:
        sid = c.execute("SELECT id FROM space WHERE review_status='published' LIMIT 1").fetchone()[0]
    r = client.post("/events", json={"dong_y": True, "phien_id": pid, "ma_thiet_bi": dev,
                                      "su_kien": [{"loai": "xem_khong_gian", "space_id": sid}] * n})
    assert r.status_code == 204


def test_deletes_this_browser_sessions_and_keeps_conversations_and_leads():
    dev = "dev" + uuid.uuid4().hex
    a, b, other = ("tfm" + uuid.uuid4().hex for _ in range(3))
    _session(a, dev, 3)
    _session(b, dev, 2)
    _session(other, "dev" + uuid.uuid4().hex, 1)  # another browser
    hid = uuid.uuid4().hex
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO hoi_thoai (id, phien_id) VALUES (%s, %s)", (hid, a))
        logs = c.execute("SELECT count(*) FROM yeu_cau_xoa_du_lieu").fetchone()[0]
    try:
        r = client.post("/privacy/xoa-du-lieu", json={"phien_id": b, "ma_thiet_bi": dev})
        assert r.json() == {"so_phien": 2, "so_su_kien": 5}
        with psycopg.connect(DSN) as c:
            assert c.execute("SELECT count(*) FROM phien_truy_cap WHERE id = ANY(%s)", ([a, b],)).fetchone()[0] == 0
            assert c.execute("SELECT count(*) FROM su_kien WHERE phien_id = ANY(%s)", ([a, b],)).fetchone()[0] == 0
            assert c.execute("SELECT phien_id FROM hoi_thoai WHERE id=%s", (hid,)).fetchone() == (None,)  # kept, detached
            assert c.execute("SELECT count(*) FROM phien_truy_cap WHERE id=%s", (other,)).fetchone()[0] == 1
            log = c.execute("SELECT so_phien, so_su_kien FROM yeu_cau_xoa_du_lieu ORDER BY id DESC LIMIT 1").fetchone()
            assert log == (2, 5) and c.execute("SELECT count(*) FROM yeu_cau_xoa_du_lieu").fetchone()[0] == logs + 1
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM hoi_thoai WHERE id=%s", (hid,))
            c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", ([a, b, other],))


def test_unknown_ids_delete_nothing_and_ids_are_required():
    assert client.post("/privacy/xoa-du-lieu", json={"phien_id": "x" * 32}).json() == {"so_phien": 0, "so_su_kien": 0}
    assert client.post("/privacy/xoa-du-lieu", json={}).status_code == 422
    assert client.post("/privacy/xoa-du-lieu", json={"phien_id": "short"}).status_code == 422
