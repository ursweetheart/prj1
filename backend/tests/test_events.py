"""Behaviour events and consent (discover-taxonomy-dimensions 1.3, 4.3). Needs the DB with a published space."""
import uuid

import psycopg

from conftest import client
from pipeline.store import DSN


def _published():
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 1").fetchone()[0]


def _count(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchone()[0]


def test_without_consent_nothing_per_visitor_is_stored():
    sid, pid = _published(), uuid.uuid4().hex
    before = _count("SELECT COALESCE(sum(so_luong), 0) FROM su_kien_an_danh WHERE ngay = current_date")
    r = client.post("/events", json={"loai": "xem_khong_gian", "dong_y": False, "phien_id": pid, "space_id": sid})
    assert r.status_code == 204
    assert _count("SELECT count(*) FROM phien_truy_cap WHERE id=%s", pid) == 0
    assert _count("SELECT count(*) FROM su_kien WHERE phien_id=%s", pid) == 0
    assert _count("SELECT COALESCE(sum(so_luong), 0) FROM su_kien_an_danh WHERE ngay = current_date") == before + 1
    with psycopg.connect(DSN) as c:  # take the test's own visit back out of the real count
        c.execute("UPDATE su_kien_an_danh SET so_luong = so_luong - 1 WHERE ngay = current_date AND loai = 'xem_khong_gian'")


def test_consented_view_is_stored_with_facet_values():
    sid, pid = _published(), uuid.uuid4().hex
    try:
        assert client.post("/events", json={"loai": "xem_khong_gian", "dong_y": True, "phien_id": pid,
                                             "space_id": sid}).status_code == 204
        with psycopg.connect(DSN) as c:
            space, values = c.execute("SELECT space_id, gia_tri FROM su_kien WHERE phien_id=%s", (pid,)).fetchone()
        assert space == sid and any(v.startswith("khong_gian:") for v in values)
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM phien_truy_cap WHERE id=%s", (pid,))  # cascades to su_kien


def test_draft_views_and_bad_input_are_not_stored():
    pid = uuid.uuid4().hex
    with psycopg.connect(DSN) as c:
        draft = c.execute("SELECT id FROM space WHERE review_status='draft' LIMIT 1").fetchone()[0]
    try:
        client.post("/events", json={"loai": "xem_khong_gian", "dong_y": True, "phien_id": pid, "space_id": draft})
        assert _count("SELECT count(*) FROM su_kien WHERE phien_id=%s", pid) == 0
        assert client.post("/events", json={"loai": "click_quang_cao", "dong_y": True, "phien_id": pid}).status_code == 422
        assert client.post("/events", json={"loai": "xem_khong_gian", "dong_y": True, "phien_id": "x"}).status_code == 422
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM phien_truy_cap WHERE id=%s", (pid,))
