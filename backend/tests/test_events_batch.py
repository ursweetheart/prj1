"""tracking-pipeline 2.1: batches with event times, session details, object types, search / similar events."""
import uuid

import psycopg

from conftest import client
from pipeline.store import DSN


def _pid():
    return "tpb" + uuid.uuid4().hex


def _published():
    with psycopg.connect(DSN) as c:
        return [r[0] for r in c.execute("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 2")]


def _drop(*pids):
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (list(pids),))


def test_a_batch_is_stored_at_the_times_the_events_happened():
    pid, (a, b) = _pid(), _published()
    body = {"dong_y": True, "phien_id": pid, "ma_thiet_bi": "dev" + uuid.uuid4().hex, "nguon": "tim_kiem",
            "thiet_bi": "di_dong", "su_kien": [
                {"loai": "luu_anh", "space_id": a, "cach_ms": 4000},
                {"loai": "xem_goi_y_tuong_tu", "space_id": a, "cach_ms": 3000},
                {"loai": "chon_goi_y", "space_id": b, "doi_tuong": str(a), "cach_ms": 1000},
                {"loai": "tim_kiem", "doi_tuong": "mo_ta", "so_ket_qua": 12}]}
    try:
        assert client.post("/events", json=body).status_code == 204
        with psycopg.connect(DSN) as c:
            rows = c.execute("SELECT loai, loai_doi_tuong, space_id, doi_tuong, so_ket_qua, "
                             "round(extract(epoch FROM now() - created_at)) FROM su_kien WHERE phien_id=%s ORDER BY created_at",
                             (pid,)).fetchall()
            sess = c.execute("SELECT nguon, thiet_bi, ma_thiet_bi IS NOT NULL, ket_thuc - bat_dau > interval '3 seconds' "
                             "FROM phien_truy_cap WHERE id=%s", (pid,)).fetchone()
        assert [r[:5] for r in rows] == [("luu_anh", "khong_gian", a, None, None), ("xem_goi_y_tuong_tu", "khong_gian", a, None, None),
                                         ("chon_goi_y", "khong_gian", b, str(a), None), ("tim_kiem", "tim_kiem", None, "mo_ta", 12)]
        assert [int(r[5]) for r in rows][:3] == [4, 3, 1]
        assert sess == ("tim_kiem", "di_dong", True, True)
    finally:
        _drop(pid)


def test_one_invalid_event_refuses_the_whole_batch():
    pid, (a, _) = _pid(), _published()
    body = {"dong_y": True, "phien_id": pid, "su_kien": [{"loai": "luu_anh", "space_id": a}, {"loai": "click_quang_cao"}]}
    assert client.post("/events", json=body).status_code == 422
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT count(*) FROM su_kien WHERE phien_id=%s", (pid,)).fetchone()[0] == 0


def test_declined_batch_counts_per_type_and_refuses_session_details():
    body = {"dong_y": False, "su_kien": [{"loai": "tim_kiem"}, {"loai": "tim_kiem"}]}
    with psycopg.connect(DSN) as c:
        q = "SELECT COALESCE(sum(so_luong), 0) FROM su_kien_an_danh WHERE loai='tim_kiem'"
        before = c.execute(q).fetchone()[0]
        assert client.post("/events", json=body).status_code == 204
        assert c.execute(q).fetchone()[0] == before + 2
    assert client.post("/events", json={**body, "nguon": "tim_kiem"}).status_code == 422


def test_similar_event_on_an_unpublished_space_stores_nothing():
    pid = _pid()
    with psycopg.connect(DSN) as c:
        draft = c.execute("SELECT id FROM space WHERE review_status='draft' LIMIT 1").fetchone()[0]
    try:
        r = client.post("/events", json={"dong_y": True, "phien_id": pid, "su_kien": [{"loai": "chon_goi_y", "space_id": draft}]})
        assert r.status_code == 204
        with psycopg.connect(DSN) as c:
            assert c.execute("SELECT count(*) FROM su_kien WHERE phien_id=%s", (pid,)).fetchone()[0] == 0
    finally:
        _drop(pid)


def test_batch_limits():
    many = {"dong_y": False, "su_kien": [{"loai": "xem_trang"}] * 51}
    assert client.post("/events", json=many).status_code == 422
    assert client.post("/events", json={"dong_y": False, "su_kien": [{"loai": "xem_trang", "cach_ms": 600_001}]}).status_code == 422
