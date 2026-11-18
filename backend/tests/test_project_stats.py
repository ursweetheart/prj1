"""Project results (change project-performance). Throw-away folders `test_ps_*` with published spaces, consented
sessions, review_log rows and leads, all removed afterwards; numbers are read for those folders only."""
import uuid
from datetime import timedelta

import psycopg
import pytest
from psycopg.types.json import Jsonb

from conftest import client
from pipeline import project_stats, rollup
from pipeline.store import DSN


@pytest.fixture
def world():
    made = {"spaces": [], "sessions": [], "leads": [], "briefs": []}

    def folder(n=1, published_days_ago=None, status="published", caption="Phòng khách sáng, gỗ sồi và vải lanh",
               style="Wabi_sabi", confidence=0.9, ingest_by=None):
        f = "test_ps_" + uuid.uuid4().hex[:8]
        ids = []
        with psycopg.connect(DSN) as c:
            for i in range(n):
                sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, style_confidence, caption, "
                                "review_status) VALUES (%s,'phong_khach',%s,%s,%s,%s) RETURNING id",
                                (f"{f}/{i}.jpg", style, confidence, caption, status)).fetchone()[0]
                ids.append(sid)
                if published_days_ago is not None:
                    c.execute("INSERT INTO review_log (space_id, action, detail, at) VALUES "
                              "(%s, 'advance', %s, now() - make_interval(days => %s))",
                              (sid, Jsonb({"from": "approved", "to": "published"}), published_days_ago))
                if ingest_by:
                    c.execute("INSERT INTO review_log (space_id, user_id, action) VALUES (%s, %s, 'ingest')", (sid, ingest_by))
        made["spaces"].extend(ids)
        return f, ids

    def session():
        pid = "t" + uuid.uuid4().hex
        with psycopg.connect(DSN) as c:
            c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
        made["sessions"].append(pid)
        return pid

    def events(space_id, loai="xem_khong_gian", n=1, days_ago=1):
        """tracking-pipeline: views and saves are read from the analytics store, so they happen on a past day,
        which is then processed as the nightly run would."""
        pid = session()
        with psycopg.connect(DSN) as c:
            for _ in range(n):
                c.execute("INSERT INTO su_kien (phien_id, loai, space_id, created_at) "
                          "VALUES (%s, %s, %s, now() - make_interval(days => %s))", (pid, loai, space_id, days_ago))
        made.setdefault("days", set()).add(rollup.local_today() - timedelta(days=days_ago))
        rollup.run(days=sorted(made["days"]))

    def lead(ngu_canh=None, brief=None, days_ago=0):
        with psycopg.connect(DSN) as c:
            bid = None
            if brief:
                bid = c.execute("INSERT INTO bo_suu_tap (loai, ma_chia_se) VALUES ('da_gui', %s) RETURNING id",
                                ("t" + uuid.uuid4().hex[:12],)).fetchone()[0]
                made["briefs"].append(bid)
                for sid in brief:
                    c.execute("INSERT INTO bo_suu_tap_anh (bo_suu_tap_id, space_id) VALUES (%s, %s)", (bid, sid))
            lid = c.execute("INSERT INTO lead (nguon, ho_ten, email, ngu_canh, bo_suu_tap_id, created_at) VALUES "
                            "('form', 'Khách thử', 'khach@example.com', %s, %s, now() - make_interval(days => %s)) "
                            "RETURNING id", (Jsonb(ngu_canh) if ngu_canh else None, bid, days_ago)).fetchone()[0]
        made["leads"].append(lid)
        return lid

    def tag(space_id, dim):
        with psycopg.connect(DSN) as c:
            c.execute("INSERT INTO space_gia_tri (space_id, gia_tri_id, nguon_tao) SELECT %s, g.id, 'nguoi' "
                      "FROM gia_tri_phan_loai g JOIN chieu_phan_loai d ON d.id = g.chieu_id WHERE d.ma_dinh_danh = %s "
                      "ORDER BY g.id LIMIT 1 ON CONFLICT DO NOTHING", (space_id, dim))

    yield type("W", (), {k: staticmethod(v) for k, v in
                         dict(folder=folder, session=session, events=events, lead=lead, tag=tag).items()} | {"made": made})
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id = ANY(%s)", (made["leads"],))
        c.execute("DELETE FROM bo_suu_tap WHERE id = ANY(%s)", (made["briefs"],))
        c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (made["sessions"],))
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made["spaces"],))
    if made.get("days"):
        rollup.run(days=sorted(made["days"]))  # the store forgets the test data too


def _ov(days=30, user_id=None):
    with psycopg.connect(DSN) as c:
        return project_stats.overview(c, days, user_id)


def _row(ov, folder):
    return next((p for p in ov["projects"] if p["folder"] == folder), None)


def _detail(folder, days=30):
    with psycopg.connect(DSN) as c:
        return project_stats.detail(c, folder, days)


# ── 1.1 overview ────────────────────────────────────────────────────────────────
def test_views_saves_and_rate(world):
    f, (a, b) = world.folder(2, published_days_ago=5)
    world.events(a, n=8)
    world.events(b, n=4)
    world.events(a, "luu_anh", n=3)
    p = _row(_ov(), f)
    assert (p["so_anh"], p["luot_xem"], p["luot_luu"], p["ti_le_luu"]) == (2, 12, 3, 25)


def test_quiz_old_events_and_drafts_are_not_counted(world):
    f, (a,) = world.folder(1, published_days_ago=5)
    _, (draft,) = world.folder(1, status="draft")
    with psycopg.connect(DSN) as c:  # a draft photo inside the same folder
        c.execute("UPDATE space SET relative_path = %s WHERE id = %s", (f"{f}/draft.jpg", draft))
    world.events(a, "chon_trac_nghiem", n=5)
    world.events(a, n=4, days_ago=40)
    world.events(draft, n=7)
    world.events(a, n=1)
    p = _row(_ov(), f)
    assert (p["so_anh"], p["luot_xem"], p["luot_luu"], p["ti_le_luu"]) == (1, 1, 0, 0)
    assert _row(_ov(90), f)["luot_xem"] == 5


def test_no_views_has_no_rate(world):
    f, _ = world.folder(1, published_days_ago=5)
    assert _row(_ov(), f)["ti_le_luu"] is None


def test_leads_from_three_sources(world):
    fa, (a1, a2) = world.folder(2, published_days_ago=5)
    fb, (b1,) = world.folder(1, published_days_ago=5)
    world.lead(brief=[a1, a2, b1])                          # A and B once each
    world.lead(ngu_canh={"trang": "/du-an/x", "du_an": fa.replace("_", "-")})  # A via its page slug
    world.lead(ngu_canh={"trang": "/khong-gian", "space_id": b1})               # B via a photo
    world.lead(ngu_canh={"du_an": fa.replace("_", "-"), "space_id": a1})        # A, counted once
    world.lead(ngu_canh={"du_an": fa.replace("_", "-")}, days_ago=40)          # outside the period
    ov = _ov()
    assert _row(ov, fa)["khach_tiem_nang"] == 3
    assert _row(ov, fb)["khach_tiem_nang"] == 2
    assert _row(_ov(90), fa)["khach_tiem_nang"] == 4


def test_no_contact_or_session_in_overview(world):
    f, (a,) = world.folder(1, published_days_ago=5)
    world.events(a)
    world.lead(ngu_canh={"space_id": a})
    text = str(_ov())
    assert "khach@example.com" not in text and "Khách thử" not in text
    assert not any(pid in text for pid in world.made["sessions"])


def test_status_rule_below_half_the_median():
    rows = [{"folder": f, "tuoi": 45, "luot_xem_cua_so": v} for f, v in zip("abcd", (40, 30, 20, 6))]
    st, cmp = project_stats.statuses(rows, 30)
    assert {f: s for f, (s, _) in st.items()} == {"a": "on", "b": "on", "c": "on", "d": "can_xem_lai"}
    assert cmp["median_views"] == 25 and cmp["du_an_du_tuoi"] == 4


def test_status_needs_three_to_compare():
    rows = [{"folder": "a", "tuoi": 45, "luot_xem_cua_so": 40}, {"folder": "b", "tuoi": 45, "luot_xem_cua_so": 0},
            {"folder": "c", "tuoi": 3, "luot_xem_cua_so": 0}]
    st, cmp = project_stats.statuses(rows, 30)
    assert st["b"] == ("on", None) and st["c"] == ("dang_theo_doi", 27) and not cmp["du_so_sanh"]


def test_young_project_is_watched_with_days_left(world, monkeypatch):
    monkeypatch.delenv("D3_PROJECT_REVIEW_DAYS", raising=False)
    f, (a,) = world.folder(1, published_days_ago=10)
    world.events(a, n=50)
    p = _row(_ov(), f)
    assert (p["trang_thai"], p["con_ngay"], p["tuoi"]) == ("dang_theo_doi", 20, 10)
    assert p["ngay_dang_uoc_tinh"] is False


def test_review_days_override(world, monkeypatch):
    monkeypatch.setenv("D3_PROJECT_REVIEW_DAYS", "0")
    f, _ = world.folder(1, published_days_ago=10)
    assert _row(_ov(), f)["trang_thai"] in ("on", "can_xem_lai")
    assert _ov()["so_sanh"]["so_ngay_danh_gia"] == 0


def test_status_does_not_follow_the_period(world, monkeypatch):
    monkeypatch.setenv("D3_PROJECT_REVIEW_DAYS", "0")
    folders = [world.folder(1, published_days_ago=40) for _ in range(4)]
    for (f, (sid,)), n in zip(folders, (40, 30, 20, 6)):
        world.events(sid, n=n, days_ago=1)
        world.events(sid, n=100, days_ago=60)  # only in the 90-day period
    s30 = {f: _row(_ov(30), f)["trang_thai"] for f, _ in folders}
    s90 = {f: _row(_ov(90), f)["trang_thai"] for f, _ in folders}
    assert s30 == s90


def test_publish_date_falls_back_to_ingest(world, as_role):
    me = client.get("/auth/me", headers=as_role("architect")).json()["id"]
    f, _ = world.folder(1, ingest_by=me)
    p = _row(_ov(), f)
    assert p["ngay_dang"] and p["ngay_dang_uoc_tinh"] is True


def test_my_projects(world, as_role):
    h = as_role("architect")
    me = client.get("/auth/me", headers=h).json()["id"]
    mine, _ = world.folder(1, published_days_ago=5, ingest_by=me)
    other, _ = world.folder(1, published_days_ago=5)
    folders = {p["folder"] for p in _ov(user_id=me)["projects"]}
    assert mine in folders and other not in folders
    r = client.get("/analytics/projects", params={"cua_toi": "true"}, headers=h).json()
    assert [p["folder"] for p in r["projects"]] == [mine]


# ── 1.2 detail ──────────────────────────────────────────────────────────────────
def _codes(d):
    return {g["ma"] for g in d["goi_y"]}


def _complete(world, n=6):
    f, ids = world.folder(n, published_days_ago=5)
    for sid in ids:
        world.tag(sid, "loai_cong_trinh")
        world.tag(sid, "muc_dau_tu")
        world.events(sid)
    return f, ids


def test_complete_project_has_nothing_to_fix(world):
    f, _ = _complete(world)
    assert _detail(f)["goi_y"] == []


def test_each_suggestion_fires(world):
    f, ids = world.folder(1, published_days_ago=5, style="Khac")
    assert {"thieu_loai_cong_trinh", "thieu_muc_dau_tu", "phong_cach_chua_ro", "it_anh"} <= _codes(_detail(f))

    f, ids = _complete(world)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET style_confidence = 0.3 WHERE id = %s", (ids[0],))
        c.execute("UPDATE space SET caption = 'Ngắn' WHERE id = %s", (ids[1],))
    d = _detail(f)
    by = {g["ma"]: g for g in d["goi_y"]}
    assert set(by) == {"phong_cach_chua_ro", "mo_ta_ngan"}
    assert by["phong_cach_chua_ro"]["anh"] == [ids[0]] and by["mo_ta_ngan"]["anh"] == [ids[1]]
    assert by["mo_ta_ngan"]["link"] == f"/quan-tri#p-{f}"


def test_unseen_photos_listed_last_and_marked(world):
    f, ids = world.folder(5, published_days_ago=5)
    for n, sid in zip((3, 5, 1, 2), ids[:4]):
        world.events(sid, n=n)
    d = _detail(f)
    assert [p["id"] for p in d["photos"]] == [ids[1], ids[0], ids[3], ids[2], ids[4]]
    assert [p["chua_ai_xem"] for p in d["photos"]] == [False] * 4 + [True]
    assert next(g for g in d["goi_y"] if g["ma"] == "anh_chua_ai_xem")["anh"] == [ids[4]]


def test_no_views_at_all_is_not_an_unseen_suggestion(world):
    f, _ = world.folder(3, published_days_ago=5)
    assert "anh_chua_ai_xem" not in _codes(_detail(f))


def test_unknown_or_unpublished_folder(world):
    f, _ = world.folder(2, status="draft")
    assert _detail(f) is None and _detail("test_ps_nope") is None


# ── 1.3 endpoints ───────────────────────────────────────────────────────────────
def test_endpoint_roles(world, as_role):
    f, (a,) = world.folder(1, published_days_ago=5)
    for role in ("architect", "lead_architect", "admin", "sales"):
        h = as_role(role)
        assert client.get("/analytics/projects", headers=h).status_code == 200
        assert client.get(f"/analytics/projects/{f}", headers=h).status_code == 200
    for role in ("visitor", "content"):
        assert client.get("/analytics/projects", headers=as_role(role)).status_code == 403
        assert client.get(f"/analytics/projects/{f}", headers=as_role(role)).status_code == 403
    assert client.get("/analytics/projects").status_code == 401
    assert client.get(f"/analytics/projects/{f}").status_code == 401


def test_endpoint_validation_and_404(world, as_role):
    h = as_role("sales")
    assert client.get("/analytics/projects", params={"days": 10}, headers=h).status_code == 422
    assert client.get("/analytics/projects/test_ps_nope", headers=h).status_code == 404
    assert client.get("/analytics/projects", params={"days": 90}, headers=h).json()["days"] == 90


def test_endpoint_has_no_session_or_contact(world, as_role):
    f, (a,) = world.folder(1, published_days_ago=5)
    world.events(a)
    world.lead(ngu_canh={"space_id": a})
    h = as_role("sales")
    for body in (client.get("/analytics/projects", headers=h).text, client.get(f"/analytics/projects/{f}", headers=h).text):
        assert "phien_id" not in body and "khach@example.com" not in body
        assert not any(pid in body for pid in world.made["sessions"])


def test_demo_flag_follows_demo_sessions(world, as_role):
    pid = "demo-" + uuid.uuid4().hex
    world.made["sessions"].append(pid)
    with psycopg.connect(DSN) as c:
        had = c.execute("SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')").fetchone()[0]
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
    assert client.get("/analytics/projects", headers=as_role("sales")).json()["co_du_lieu_mo_phong"] is True
    if not had:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM phien_truy_cap WHERE id = %s", (pid,))
        assert client.get("/analytics/projects", headers=as_role("sales")).json()["co_du_lieu_mo_phong"] is False


# ── project-catalog 4.1: a catalog project groups its photos whatever their folder ──────────────────────────────────
def test_catalog_project_named_and_counts_its_page_leads(world):
    f1, (a,) = world.folder(1, published_days_ago=5)
    f2, (b,) = world.folder(1, published_days_ago=5)
    slug = "test-ps-cat-" + uuid.uuid4().hex[:6]
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO du_an (slug, ten, thu_tu, co_trang) VALUES (%s, 'Căn hộ thử', 998, true)", (slug,))
        c.execute("UPDATE space SET du_an_slug = %s WHERE id = ANY(%s)", (slug, [a, b]))
    try:
        world.lead(ngu_canh={"trang": f"/du-an/{slug}", "du_an": slug})
        row = _row(_ov(), slug)
        assert (row["ten"], row["so_anh"], row["khach_tiem_nang"]) == ("Căn hộ thử", 2, 1)
        assert row["thu_muc"] in (f1, f2) and _row(_ov(), f1) is None and _row(_ov(), f2) is None
        assert {g["link"] for g in _detail(slug)["goi_y"]} <= {f"/quan-tri#p-{row['thu_muc']}"}
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE space SET du_an_slug = NULL WHERE id = ANY(%s)", ([a, b],))
            c.execute("DELETE FROM du_an WHERE slug = %s", (slug,))
