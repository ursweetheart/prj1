"""Behaviour events (change behaviour-events). Throw-away consented sessions; anonymous counts checked as differences."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import behaviour, leads
from pipeline.store import DSN

TAG = uuid.uuid4().hex[:6]


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def pid():
    p = "t" + uuid.uuid4().hex
    yield p
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM phien_truy_cap WHERE id = %s", (p,))


def send(pid, loai, **kw):
    return client.post("/events", json={"loai": loai, "dong_y": True, "phien_id": pid, **kw})


def _anon(loai):
    r = _q("SELECT so_luong FROM su_kien_an_danh WHERE ngay = current_date AND loai = %s", loai)
    return r[0][0] if r else 0


# ── 1.2 ─────────────────────────────────────────────────────────────────────────
def test_consented_project_view_stored_as_sent(pid):
    r = send(pid, "xem_du_an", trang="/du-an/:slug", doi_tuong="beaumont-lounge", thoi_gian_dung_ms=40000, do_sau_cuon=1)
    assert r.status_code == 204
    assert _q("SELECT loai, trang, doi_tuong, thoi_gian_dung_ms, do_sau_cuon, space_id FROM su_kien WHERE phien_id = %s", pid) == \
        [("xem_du_an", "/du-an/:slug", "beaumont-lounge", 40000, 1.0, None)]


def test_unconsented_counts_only():
    before = _anon("bam_CTA")
    r = client.post("/events", json={"loai": "bam_CTA", "dong_y": False, "doi_tuong": "/lien-he", "trang": "/"})
    assert r.status_code == 204 and _anon("bam_CTA") == before + 1


@pytest.mark.parametrize("bad", [
    {"trang": "/bo-suu-tap/xem/ABC123?x=1"}, {"trang": "lien-he"}, {"doi_tuong": "a b"}, {"doi_tuong": "x" * 101},
    {"gia_tri": ["Phong cach"]}, {"gia_tri": ["a:b"] * 21}, {"thoi_gian_dung_ms": -1},
    {"thoi_gian_dung_ms": 86_400_001}, {"do_sau_cuon": 1.5}, {"loai": "bam_hotspot"},
])
def test_invalid_fields(pid, bad):
    body = {"loai": "xem_trang", "dong_y": True, "phien_id": pid, "trang": "/", **bad}
    assert client.post("/events", json=body).status_code == 422


def test_filter_values_stored(pid):
    assert send(pid, "ap_dung_bo_loc", trang="/khong-gian", gia_tri=["phong_cach:Japandi", "khong_gian:phong_khach"]).status_code == 204
    assert _q("SELECT gia_tri FROM su_kien WHERE phien_id = %s", pid)[0][0] == ["phong_cach:Japandi", "khong_gian:phong_khach"]


def test_photo_events_unchanged(pid):
    sid = _q("SELECT id FROM space WHERE review_status = 'published' ORDER BY id LIMIT 1")[0][0]
    assert send(pid, "xem_khong_gian", space_id=sid).status_code == 204
    (loai, space, tags), = _q("SELECT loai, space_id, gia_tri FROM su_kien WHERE phien_id = %s", pid)
    assert (loai, space) == ("xem_khong_gian", sid) and tags


def test_profile_counts_photo_events_only(pid):
    ids = [r[0] for r in _q("SELECT id FROM space WHERE review_status = 'published' ORDER BY id LIMIT 3")]
    for sid in ids:
        send(pid, "xem_khong_gian", space_id=sid)
    for _ in range(5):
        send(pid, "xem_trang", trang="/uoc-tinh", thoi_gian_dung_ms=1000, do_sau_cuon=0.5)
    profile = leads.behaviour_profile(pid)
    assert profile["views"] == 3 and len(profile["spaces"]) == 3, profile


# ── 1.3 ─────────────────────────────────────────────────────────────────────────
def _ov():
    with psycopg.connect(DSN) as c:
        return behaviour.overview(c, 30)


def test_overview_aggregates(pid):
    page = f"/test-{TAG}"
    send(pid, "xem_trang", trang=page, thoi_gian_dung_ms=20000, do_sau_cuon=0.5)
    send(pid, "xem_trang", trang=page, thoi_gian_dung_ms=40000, do_sau_cuon=1)
    send(pid, "xem_du_an", trang="/du-an/:slug", doi_tuong=f"test-{TAG}", thoi_gian_dung_ms=10000, do_sau_cuon=1)
    for target, at in (("/lien-he", "/"), ("/lien-he", "/"), ("/lien-he", f"/test-{TAG}"), (f"/test-{TAG}", "/")):
        send(pid, "bam_CTA", doi_tuong=target, trang=at)
    send(pid, "gui_form", doi_tuong=f"test_{TAG}")
    send(pid, "chia_se", doi_tuong=f"test_{TAG}")
    send(pid, "nhan_chatbot")
    send(pid, "ap_dung_bo_loc", trang="/khong-gian", gia_tri=[f"test_{TAG}:A", f"test_{TAG}:B"])
    send(pid, "ap_dung_bo_loc", trang="/khong-gian", gia_tri=[f"test_{TAG}:A"])
    ov = _ov()
    p = next(x for x in ov["trang"] if x["trang"] == page)
    assert (p["luot_xem"], p["giay_tb"], p["cuon_tb"]) == (2, 30, 75)
    assert next(x for x in ov["du_an"] if x["du_an"] == f"test-{TAG}")["luot_xem"] == 1
    mine = next(c for c in ov["cta"] if c["dich"] == f"/test-{TAG}")
    assert mine["so_lan"] == 1 and mine["tu_trang"] == [{"trang": "/", "so_lan": 1}]
    lh = next(c for c in ov["cta"] if c["dich"] == "/lien-he")
    assert {"trang": f"/test-{TAG}", "so_lan": 1} in lh["tu_trang"]
    assert ov["form"][f"test_{TAG}"] == 1 and ov["chia_se"][f"test_{TAG}"] == 1
    assert {"gia_tri": f"test_{TAG}:A", "so_lan": 2} in ov["bo_loc"] or len(ov["bo_loc"]) == behaviour.TOP
    assert ov["dong_y"]["nhan_chatbot"] >= 1 and set(ov["an_danh"]) == set(behaviour.TYPES)


def test_endpoint_roles_and_no_session(pid, as_role):
    send(pid, "xem_trang", trang="/", thoi_gian_dung_ms=1000, do_sau_cuon=0.2)
    r = client.get("/analytics/behaviour", headers=as_role("sales"))
    assert r.status_code == 200 and pid not in r.text and "phien_id" not in r.text
    assert client.get("/analytics/behaviour", headers=as_role("lead_architect")).status_code == 200
    assert client.get("/analytics/behaviour", headers=as_role("visitor")).status_code == 403
    assert client.get("/analytics/behaviour").status_code == 401
    assert client.get("/analytics/behaviour", params={"days": 10}, headers=as_role("sales")).status_code == 422
