"""Trend dashboard (change trend-dashboard): save events, interest score and trends, the overview endpoint, demo
activity. Counts are checked as differences, so real events already in the database do not matter."""
import json
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import demo_activity, discovery, trends
from pipeline.store import DSN
from psycopg.types.json import Jsonb


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def world():
    """A throw-away consented session and published spaces; everything removed afterwards."""
    made = {"spaces": [], "sessions": [], "leads": []}

    def space(style="Wabi_sabi", room="phong_khach"):
        with psycopg.connect(DSN) as c:
            sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, palette, review_status) "
                            "VALUES (%s,%s,%s,%s,'published') RETURNING id",
                            (f"test_{uuid.uuid4().hex[:8]}/x.jpg", room, style,
                             Jsonb({"brightness": "light", "temperature": "warm"}))).fetchone()[0]
        made["spaces"].append(sid)
        return sid

    def session():
        pid = "t" + uuid.uuid4().hex
        with psycopg.connect(DSN) as c:
            c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
        made["sessions"].append(pid)
        return pid

    def events(pid, space_id, loai="xem_khong_gian", n=1, days_ago=0):
        with psycopg.connect(DSN) as c:
            for _ in range(n):
                c.execute("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri, created_at) SELECT %s, %s, s.id, "
                          "COALESCE((SELECT array_agg(d.ma_dinh_danh || ':' || v.ma_dinh_danh) FROM space_gia_tri sg "
                          "JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id "
                          "WHERE sg.space_id = s.id), '{}'), now() - make_interval(days => %s) FROM space s WHERE s.id = %s",
                          (pid, loai, days_ago, space_id))

    yield type("W", (), {"space": staticmethod(space), "session": staticmethod(session), "events": staticmethod(events),
                         "made": made})
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id = ANY(%s)", (made["leads"],))
        c.execute("DELETE FROM bo_suu_tap WHERE id IN (SELECT bo_suu_tap_id FROM bo_suu_tap_anh WHERE space_id = ANY(%s))",
                  (made["spaces"],))
        c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (made["sessions"],))
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made["spaces"],))


def _overview(days=30):
    with psycopg.connect(DSN) as c:
        return trends.overview(c, days)


def _value(ov, dim, code):
    d = next(d for d in ov["chieu"] if d["ma"] == dim)
    return next((v for v in d["gia_tri"] if v["ma"] == code), {"xem": 0, "luu": 0, "brief": 0, "diem": 0})


# ── 1.1 save events ────────────────────────────────────────────────────────────
def test_consented_save_is_stored_with_snapshot(world):
    sid, pid = world.space(), "t" + uuid.uuid4().hex
    world.made["sessions"].append(pid)
    r = client.post("/events", json={"loai": "luu_anh", "dong_y": True, "phien_id": pid, "space_id": sid})
    assert r.status_code == 204
    loai, tags = _q("SELECT loai, gia_tri FROM su_kien WHERE phien_id=%s", pid)[0]
    assert loai == "luu_anh" and "phong_cach:Wabi_sabi" in tags


def test_save_without_consent_counts_anonymously(world):
    before = _q("SELECT COALESCE(sum(so_luong),0) FROM su_kien_an_danh WHERE ngay=current_date AND loai='luu_anh'")[0][0]
    assert client.post("/events", json={"loai": "luu_anh", "dong_y": False}).status_code == 204
    assert _q("SELECT sum(so_luong) FROM su_kien_an_danh WHERE ngay=current_date AND loai='luu_anh'")[0][0] == before + 1
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE su_kien_an_danh SET so_luong = so_luong - 1 WHERE ngay=current_date AND loai='luu_anh'")


def test_demo_prefix_is_reserved():
    r = client.post("/events", json={"loai": "xem_khong_gian", "dong_y": True, "phien_id": "demo-" + uuid.uuid4().hex,
                                     "space_id": 1})
    assert r.status_code == 422


# ── 2.1 score, share, trend ────────────────────────────────────────────────────
def test_weighted_score_and_shares():
    assert trends.score(xem=10, luu=2, brief=1) == 21
    assert trends.shares({"phong_cach:Wabi_sabi": 21, "phong_cach:Indochine": 9, "phong_cach:Khac": 5}) == \
        {"phong_cach:Wabi_sabi": 70, "phong_cach:Indochine": 30}


def test_trend_rule():
    assert trends.trend([12, 4, 6, 5, 5], signals0=8) == {"thay_doi": 140, "xu_huong": "dang_tang"}
    assert trends.trend([3, 1, 1, 1, 1], signals0=3)["xu_huong"] is None  # too little activity
    assert trends.trend([6, 0, 0, 0, 0], signals0=6) == {"thay_doi": None, "xu_huong": "moi_noi"}
    assert trends.trend([2, 10, 10, 10, 10], signals0=2) == {"thay_doi": -80, "xu_huong": "dang_giam"}
    assert trends.trend([2, 2, 2, 2, 2], signals0=2)["xu_huong"] is None  # small average never "falls"


# ── 2.2 overview ───────────────────────────────────────────────────────────────
def test_overview_counts_and_trends(world):
    a, b = world.space("Wabi_sabi"), world.space("Indochine")
    pid = world.session()
    before = _overview(30)
    world.events(pid, a, n=4)                      # this week
    world.events(pid, a, "luu_anh", n=2)
    world.events(pid, b, n=3, days_ago=12)         # two weeks ago
    with psycopg.connect(DSN) as c:
        cid = c.execute("INSERT INTO bo_suu_tap (loai, ma_chia_se) VALUES ('da_gui', %s) RETURNING id",
                        (uuid.uuid4().hex,)).fetchone()[0]
        c.execute("INSERT INTO bo_suu_tap_anh (bo_suu_tap_id, space_id) VALUES (%s, %s)", (cid, a))
        world.made["leads"].append(c.execute("INSERT INTO lead (nguon, ho_ten) VALUES ('estimate', 'T') RETURNING id").fetchone()[0])
    after = _overview(30)
    w_b, w_a = _value(before, "phong_cach", "Wabi_sabi"), _value(after, "phong_cach", "Wabi_sabi")
    assert (w_a["xem"] - w_b["xem"], w_a["luu"] - w_b["luu"], w_a["brief"] - w_b["brief"]) == (4, 2, 1)
    assert w_a["diem"] - w_b["diem"] == 4 + 6 + 5
    assert _value(after, "phong_cach", "Indochine")["xem"] - _value(before, "phong_cach", "Indochine")["xem"] == 3
    t_b, t_a = before["tong"], after["tong"]
    assert t_a["luot_xem_dong_y"] - t_b["luot_xem_dong_y"] == 7 and t_a["luot_luu"] - t_b["luot_luu"] == 2
    assert t_a["brief"] - t_b["brief"] == 1 and t_a["lead"]["estimate"] - t_b["lead"]["estimate"] == 1
    assert len(after["lead_theo_tuan"]) == 8 and after["lead_theo_tuan"][-1]["estimate"] >= 1
    assert _overview(7)["tong"]["luot_xem_dong_y"] - _overview(7)["tong"]["luot_xem_dong_y"] == 0  # stable


def test_top_spaces_and_order(world):
    a = world.space("Japandi")
    pid = world.session()
    world.events(pid, a, n=60)
    ov = _overview(7)
    assert ov["khong_gian_xem_nhieu"][0]["id"] == a and ov["khong_gian_xem_nhieu"][0]["luot_xem"] >= 60
    styles = next(d for d in ov["chieu"] if d["ma"] == "phong_cach")["gia_tri"]
    assert styles == sorted(styles, key=lambda v: -v["diem"]) and all(v["ma"].lower() != "khac" for v in styles)


def test_endpoint_roles_and_no_session_ids(world, as_role):
    pid = world.session()
    world.events(pid, world.space(), n=2)
    r = client.get("/analytics/overview", params={"days": 7}, headers=as_role("sales"))
    assert r.status_code == 200 and pid not in r.text and "phien_id" not in r.text
    assert client.get("/analytics/overview", headers=as_role("lead_architect")).status_code == 200
    assert client.get("/analytics/overview", headers=as_role("visitor")).status_code == 403
    assert client.get("/analytics/overview").status_code == 401
    assert client.get("/analytics/overview", params={"days": 10}, headers=as_role("sales")).status_code == 422


# ── 3.1 demo activity ──────────────────────────────────────────────────────────
def test_demo_generate_rerun_remove(world):
    real = world.session()
    try:
        with psycopg.connect(DSN) as c:
            made = demo_activity.generate(c, sessions=240, seed=7)
        n1 = _q("SELECT count(*) FROM phien_truy_cap WHERE id LIKE 'demo-%%'")[0][0]
        span = _q("SELECT max(created_at) - min(created_at) FROM su_kien WHERE phien_id LIKE 'demo-%%'")[0][0]
        assert n1 == 240 and span.days >= 50
        ov = _overview(30)
        assert ov["co_du_lieu_mo_phong"] is True
        rising = [a for a in ov["canh_bao"] if a["chieu"] == "Phong cách" and a["xu_huong"] in ("dang_tang", "moi_noi")]
        assert any(a["ma"] == made["rising_style"] for a in rising), ov["canh_bao"]
        with psycopg.connect(DSN) as c:
            demo_activity.generate(c, sessions=240, seed=7)
        assert _q("SELECT count(*) FROM phien_truy_cap WHERE id LIKE 'demo-%%'")[0][0] == n1  # replaced, not added
        # discovery's behaviour lift ignores demo views
        space_ids = {r[0] for r in _q("SELECT DISTINCT space_id FROM su_kien WHERE phien_id LIKE 'demo-%%' LIMIT 5")}
        with_demo = discovery._space_facts(space_ids)["do_nang_xem"]
    finally:
        with psycopg.connect(DSN) as c:
            demo_activity.remove(c)
    assert discovery._space_facts(space_ids)["do_nang_xem"] == with_demo  # demo rows never counted
    assert _q("SELECT count(*) FROM phien_truy_cap WHERE id LIKE 'demo-%%'")[0][0] == 0
    assert _q("SELECT count(*) FROM phien_truy_cap WHERE id=%s", real)[0][0] == 1
    assert _overview(30)["co_du_lieu_mo_phong"] is False
