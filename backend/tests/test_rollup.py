"""tracking-pipeline 3.1 / 3.2: nightly processing and taste groups. Test events live on dates in 2001, which hold no
real data, and everything is removed afterwards."""
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest

from pipeline import rollup, taste_groups
from pipeline.store import DSN

D = date(2001, 2, 5)
VN = timezone(timedelta(hours=7))


def at(d, h=10, m=0, s=0):
    return datetime(d.year, d.month, d.day, h, m, s, tzinfo=VN)


@pytest.fixture
def db():
    made = []
    with psycopg.connect(DSN) as c:
        space, slug = c.execute("SELECT id, du_an_slug FROM space WHERE review_status='published' AND du_an_slug IS NOT NULL "
                                "ORDER BY id LIMIT 1").fetchone()

        def session():
            pid = "trl" + uuid.uuid4().hex
            c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
            made.append(pid)
            return pid

        def event(pid, loai, when, **kw):
            c.execute("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri, created_at, thoi_gian_dung_ms, trang, doi_tuong) "
                      "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                      (pid, loai, kw.get("space_id"), kw.get("gia_tri", []), when, kw.get("ms"), kw.get("trang"), kw.get("doi_tuong")))
        yield c, session, event, space, slug
        c.rollback()
        c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (made,))
        for t in ("tk_ngay", "tk_gia_tri_ngay", "tk_khong_gian_ngay", "tk_hanh_vi_ngay", "tk_tong_ngay", "phien_bat_thuong"):
            c.execute(f"DELETE FROM {t} WHERE ngay < '2002-01-01'")
        c.execute("DELETE FROM tk_xu_huong WHERE ngay_tinh < '2002-01-01'")
        c.execute("DELETE FROM tk_nhom_chay WHERE ngay_tinh < '2002-01-01'")
        c.commit()


def test_dwell_from_the_next_event_capped_and_none_for_the_last(db):
    c, session, event, space, _ = db
    p = session()
    event(p, "xem_khong_gian", at(D, 10, 0, 0), space_id=space)
    event(p, "xem_khong_gian", at(D, 10, 0, 45), space_id=space)
    event(p, "xem_trang", at(D, 10, 1, 0), ms=3_600_000, trang="/")  # measured by the browser: capped at 30 min
    event(p, "xem_khong_gian", at(D, 11, 0, 0), space_id=space)       # last event of the session
    rollup.process_day(c, D)
    got = [r[0] for r in c.execute("SELECT dung_thuc_ms FROM su_kien WHERE phien_id=%s ORDER BY created_at", (p,))]
    assert got == [45_000, 15_000, 1_800_000, None]


@pytest.mark.parametrize("rule", ["burst", "fast", "many"])
def test_each_abnormal_rule_drops_the_session(db, rule):
    c, session, event, space, _ = db
    good, bad = session(), session()
    event(good, "xem_khong_gian", at(D), space_id=space, gia_tri=["phong_cach:Test_ab"])
    if rule == "burst":
        for i in range(60):
            event(bad, "xem_khong_gian", at(D, 12, 0, i % 60), space_id=space, gia_tri=["phong_cach:Test_ab"])
    elif rule == "fast":
        for i in range(20):
            event(bad, "xem_trang", at(D, 12, i, 0), ms=500, trang="/")
        event(bad, "xem_khong_gian", at(D, 13), space_id=space, gia_tri=["phong_cach:Test_ab"])
    else:
        for i in range(501):
            event(bad, "xem_khong_gian", at(D, 1 + i // 50, i % 50, 0), space_id=space, gia_tri=["phong_cach:Test_ab"])
    rollup.process_day(c, D)
    assert [r[0] for r in c.execute("SELECT phien_id FROM phien_bat_thuong WHERE ngay=%s", (D,))] == [bad]
    assert c.execute("SELECT so_xem, so_phien FROM tk_gia_tri_ngay WHERE ngay=%s AND gia_tri='phong_cach:Test_ab'",
                     (D,)).fetchone() == (1, 1)
    assert c.execute("SELECT so_phien_bat_thuong FROM tk_ngay WHERE ngay=%s", (D,)).fetchone() == (1,)


def test_daily_aggregates_and_rerun_replaces(db):
    c, session, event, space, _ = db
    p, q = session(), session()
    for who in (p, p, q):
        event(who, "xem_khong_gian", at(D, 9), space_id=space, gia_tri=["phong_cach:Test_ag", "tong_mau:Test_am"])
    event(p, "luu_anh", at(D, 9, 5), space_id=space, gia_tri=["phong_cach:Test_ag"])
    event(p, "ap_dung_bo_loc", at(D, 9, 6), gia_tri=["phong_cach:Test_ag", "tong_mau:Test_am"])
    event(q, "xem_goi_y_tuong_tu", at(D, 9, 7), space_id=space, doi_tuong=str(space))
    event(q, "chon_goi_y", at(D, 9, 8), space_id=space, doi_tuong=str(space))
    for _ in range(2):  # running a day twice gives the same figures
        rollup.process_day(c, D)
        assert c.execute("SELECT so_xem, so_luu, so_phien FROM tk_gia_tri_ngay WHERE ngay=%s AND gia_tri='phong_cach:Test_ag'",
                         (D,)).fetchone() == (3, 1, 2)
        assert c.execute("SELECT so_xem, so_luu FROM tk_khong_gian_ngay WHERE ngay=%s AND space_id=%s", (D, space)).fetchone() == (3, 1)
        beh = dict(c.execute("SELECT loai || '/' || doi_tuong, so_luot FROM tk_hanh_vi_ngay WHERE ngay=%s", (D,)).fetchall())
        assert beh == {"ap_dung_bo_loc/phong_cach:Test_ag": 1, "ap_dung_bo_loc/tong_mau:Test_am": 1,
                       "xem_goi_y_tuong_tu/": 1, "chon_goi_y/": 1}
    cols = {r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_name LIKE 'tk\\_%%'")}
    assert not any("phien_id" in col for col in cols)  # the store holds no session id


def test_project_view_gets_its_published_spaces_values(db):
    c, session, event, _, slug = db
    p = session()
    event(p, "xem_du_an", at(D), trang="/du-an/:slug", doi_tuong=slug)
    rollup.process_day(c, D)
    vals = c.execute("SELECT gia_tri FROM su_kien WHERE phien_id=%s", (p,)).fetchone()[0]
    want = {r[0] for r in c.execute(
        "SELECT DISTINCT d.ma_dinh_danh || ':' || g.ma_dinh_danh FROM space s JOIN space_gia_tri sg ON sg.space_id = s.id "
        "JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = g.chieu_id "
        "WHERE s.du_an_slug=%s AND s.review_status='published'", (slug,))}
    assert vals and set(vals) == want


def test_stored_trend_matches_the_interest_score_rules(db):
    c, *_ = db
    end = date(2001, 3, 31)
    for w, score in enumerate([12, 5, 5, 6, 4]):  # week 0 = last 7 days ... 4 weeks before (views only, weight 1)
        c.execute("INSERT INTO tk_gia_tri_ngay (ngay, gia_tri, so_xem) VALUES (%s, 'phong_cach:Test_tr', %s)",
                  (end - timedelta(days=7 * w), score))
    rollup.store_trends(c, end)
    assert c.execute("SELECT tuan0, so_tin_hieu, thay_doi, xu_huong FROM tk_xu_huong WHERE ngay_tinh=%s AND gia_tri='phong_cach:Test_tr'",
                     (end,)).fetchone() == (12, 12, 140, "dang_tang")


def test_pending_days_stop_before_today_and_today_is_never_run():
    now = datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc)  # 10:00 in Vietnam
    with psycopg.connect(DSN) as c:
        days = rollup.pending_days(c, now)
    assert all(d < date(2026, 11, 18) for d in days)
    assert rollup.run(days=[rollup.local_today()]) == []


def test_due_only_from_one_in_the_morning():
    assert rollup.due_and_run(datetime(2026, 11, 18, 17, 30, tzinfo=timezone.utc)) == []  # 00:30 UTC+7


# ── taste groups (pure) ──────────────────────────────────────────────────────────────────────────────────────────
POOL = ["tong_mau:am", "tong_mau:trung_tinh", "tong_mau:tram", "khong_gian:phong_khach", "khong_gian:phong_ngu", "vat_lieu:da"]


def _population(n, vals, _extra, seed=1):
    """n sessions mostly on vals, each with its own counts and 1-2 values from a pool every population shares."""
    import random
    rnd = random.Random(seed + len(vals[0]))
    return {f"{vals[0]}{i}": Counter({v: rnd.randint(2, 5) for v in vals} | {rnd.choice(POOL): 1 for _ in range(rnd.randint(1, 2))})
            for i in range(n)}


def test_two_clear_populations_give_two_groups_with_their_values():
    sessions = _population(15, ["phong_cach:Wabi_sabi", "vat_lieu:go"], ["tong_mau:am", "tong_mau:trung_tinh"]) | \
        _population(15, ["phong_cach:Indochine", "vat_lieu:may_tre"], ["tong_mau:tram", "tong_mau:am"])
    found = taste_groups.groups(sessions)
    assert len(found) == 2 and sum(g["so_phien"] for g in found) == 30
    tops = {frozenset(g["gia_tri"][:2]) for g in found}
    assert frozenset({"phong_cach:Wabi_sabi", "vat_lieu:go"}) in tops
    assert frozenset({"phong_cach:Indochine", "vat_lieu:may_tre"}) in tops


def test_too_few_sessions_is_no_grouping():
    assert taste_groups.groups(_population(9, ["phong_cach:Japandi"], ["tong_mau:am"])) is None


def test_new_only_when_the_pair_led_no_recent_group():
    found = [{"gia_tri": ["phong_cach:Japandi", "mau_sac:xanh_reu", "vat_lieu:go"]}, {"gia_tri": ["phong_cach:Indochine", "vat_lieu:go"]}]
    out = taste_groups.mark_new(found, {("phong_cach:Indochine", "vat_lieu:go")})
    assert [g["moi"] for g in out] == [True, False]
