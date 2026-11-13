"""Saved collections and design briefs (change saved-collection-brief). Uses throw-away published spaces whose tags
come from the sync_ai_tags trigger (space_type, design_style, palette), removed after each test."""
import re
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import bo_suu_tap, leads, notify
from pipeline.store import DSN
from psycopg.types.json import Jsonb

BRIEF = {"ho_ten": "Lan", "so_dien_thoai": "0912345678", "loai_nha": "can_ho", "dien_tich_m2": 70,
         "ngan_sach": "300tr_700tr", "loi_nhan": "Muốn phòng khách ấm", "t_ms": 8000}


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def spaces():
    """spaces([(space_type, design_style, brightness, temperature), ...], status='published') -> ids."""
    made = []

    def make(specs, status="published"):
        folder = "test_" + uuid.uuid4().hex[:8]
        with psycopg.connect(DSN) as c:
            for n, (st, ds, br, te) in enumerate(specs):
                made.append(c.execute(
                    "INSERT INTO space (relative_path, space_type, design_style, palette, review_status) "
                    "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                    (f"{folder}/{n}.jpg", st, ds, Jsonb({"brightness": br, "temperature": te}), status)).fetchone()[0])
        return made[-len(specs):]

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE bo_suu_tap_id IN (SELECT bo_suu_tap_id FROM bo_suu_tap_anh WHERE space_id = ANY(%s))",
                  (made,))
        c.execute("DELETE FROM bo_suu_tap WHERE id IN (SELECT bo_suu_tap_id FROM bo_suu_tap_anh WHERE space_id = ANY(%s))",
                  (made,))
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made,))


@pytest.fixture
def no_mail(monkeypatch):
    calls = []
    monkeypatch.setattr(notify, "notify_new_lead", lambda i: calls.append(("sales", i)))
    monkeypatch.setattr(notify, "confirm_to_visitor", lambda i: calls.append(("visitor", i)))
    return calls


ROOM = ("phong_khach", "Wabi_sabi", "light", "warm")
FIVE = [("phong_khach", "Wabi_sabi", "light", "warm"), ("phong_khach", "Wabi_sabi", "dark", "warm"),
        ("phong_khach", "Wabi_sabi", "light", "warm"), ("bep_va_an", "Japandi", "dark", "warm"),
        ("khac", "Khac", "light", "cool")]


def _items(sids, notes=None):
    return [{"space_id": s, "ghi_chu": (notes or {}).get(s)} for s in sids]


# ── 2.1 GET /spaces?ids= ───────────────────────────────────────────────────────
def test_ids_filter_returns_only_published_to_visitors(spaces):
    pub = spaces([ROOM, ROOM])
    draft = spaces([ROOM], status="draft")
    got = client.get("/spaces", params={"ids": ",".join(map(str, pub + draft))}).json()
    assert sorted(r["id"] for r in got) == sorted(pub)
    assert client.get("/spaces", params={"ids": ",".join(str(i) for i in range(1, 62))}).status_code == 422
    assert client.get("/spaces", params={"ids": "1,x"}).status_code == 422


# ── 2.2 account collection ─────────────────────────────────────────────────────
def test_add_note_remove_and_errors(spaces, as_role):
    me = as_role("visitor")
    a, b = spaces([ROOM, ROOM])
    [draft] = spaces([ROOM], status="draft")
    assert client.put(f"/collections/me/items/{a}", json={}, headers=me).status_code == 200
    got = client.put(f"/collections/me/items/{a}", json={"ghi_chu": "  thích màu gỗ "}, headers=me).json()
    assert [(r["space_id"], r["ghi_chu"]) for r in got] == [(a, "thích màu gỗ")]
    client.put(f"/collections/me/items/{b}", json={}, headers=me)
    assert client.delete(f"/collections/me/items/{a}", headers=me).status_code == 204
    assert [r["space_id"] for r in client.get("/collections/me", headers=me).json()] == [b]
    assert client.put(f"/collections/me/items/{draft}", json={}, headers=me).status_code == 404
    assert client.get("/collections/me").status_code == 401
    assert client.put(f"/collections/me/items/{a}", json={"ghi_chu": "x" * 301}, headers=me).status_code == 422


def test_full_at_60(spaces, as_role):
    me = as_role("visitor")
    ids = spaces([ROOM] * 61)
    client.post("/collections/me/merge", json={"items": _items(ids[:60])}, headers=me)
    assert len(client.get("/collections/me", headers=me).json()) == 60
    r = client.put(f"/collections/me/items/{ids[60]}", json={}, headers=me)
    assert r.status_code == 409 and r.json()["detail"] == "bo_suu_tap_day"
    assert client.put(f"/collections/me/items/{ids[0]}", json={"ghi_chu": "ok"}, headers=me).status_code == 200  # edit still fine


def test_merge_fills_empty_notes_keeps_account_notes(spaces, as_role):
    me = as_role("visitor")
    a, b, c = spaces([ROOM, ROOM, ROOM])
    client.put(f"/collections/me/items/{a}", json={}, headers=me)                       # no note in the account
    client.put(f"/collections/me/items/{b}", json={"ghi_chu": "giữ nguyên"}, headers=me)
    got = client.post("/collections/me/merge", headers=me, json={"items": _items(
        [a, b, c, a], {a: "thích màu gỗ", b: "ghi đè?", c: "mới"})}).json()
    assert {r["space_id"]: r["ghi_chu"] for r in got} == {a: "thích màu gỗ", b: "giữ nguyên", c: "mới"}


def test_unpublished_space_disappears(spaces, as_role):
    me = as_role("visitor")
    a, b = spaces([ROOM, ROOM])
    client.post("/collections/me/merge", json={"items": _items([a, b])}, headers=me)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status='draft' WHERE id=%s", (b,))
    assert [r["space_id"] for r in client.get("/collections/me", headers=me).json()] == [a]


# ── 3.1 summary ────────────────────────────────────────────────────────────────
def test_brief_summary_spec_example(spaces):
    s = leads.brief_summary(spaces(FIVE))
    assert s["line"] == "Wabi-sabi 60% · tông Ấm · phòng khách" and s["n"] == 5


def test_brief_summary_single_photo_and_no_khac(spaces):
    assert leads.brief_summary(spaces([("bep_va_an", "Khac", "dark", "cool")]))["line"] == "tông Lạnh · bếp & phòng ăn"
    assert not re.search(r"(^|[ ·,])khác( |$|,|·)", leads.brief_summary(spaces(FIVE))["line"].lower())  # not "khách"


# ── 3.2 POST /briefs and the shared view ───────────────────────────────────────
def test_anonymous_brief_creates_lead_and_frozen_copy(spaces, no_mail):
    ids = spaces(FIVE)
    r = client.post("/briefs", json={**BRIEF, "items": _items(ids, {ids[0]: "thích sofa"})})
    assert r.status_code == 201 and "0912345678" in r.json()["message"]
    lid, code = r.json()["lead_id"], r.json()["ma_chia_se"]
    nguon, req, coll = _q("SELECT nguon, request, bo_suu_tap_id FROM lead WHERE id=%s", lid)[0]
    assert nguon == "brief" and req["loai_nha"] == "can_ho" and req["dien_tich_m2"] == 70
    assert req["tom_tat"]["line"] == "Wabi-sabi 60% · tông Ấm · phòng khách" and coll
    assert no_mail == [("sales", lid), ("visitor", lid)]
    shared = client.get(f"/collections/shared/{code}").json()
    assert [i["id"] for i in shared["items"]] == ids and shared["items"][0]["ghi_chu"] == "thích sofa"
    assert "Lan" not in str(shared) and "0912345678" not in str(shared)


def test_sent_copy_does_not_follow_later_edits(spaces, as_role, no_mail):
    me = as_role("visitor")
    a, b = spaces([ROOM, ROOM])
    client.post("/collections/me/merge", json={"items": _items([a, b])}, headers=me)
    code = client.post("/briefs", json={**BRIEF, "items": _items([a, b])}, headers=me).json()["ma_chia_se"]
    client.delete(f"/collections/me/items/{b}", headers=me)
    assert [i["id"] for i in client.get(f"/collections/shared/{code}").json()["items"]] == [a, b]
    assert [r["space_id"] for r in client.get("/collections/me", headers=me).json()] == [a]  # collection kept


def test_brief_without_published_space_stores_nothing(spaces, no_mail):
    [draft] = spaces([ROOM], status="draft")
    before = _q("SELECT count(*) FROM lead")[0][0]
    r = client.post("/briefs", json={**BRIEF, "items": _items([draft])})
    assert r.status_code == 422 and r.json()["detail"][0]["loc"][-1] == "items"
    assert client.post("/briefs", json={**BRIEF, "items": []}).status_code == 422
    assert _q("SELECT count(*) FROM lead")[0][0] == before and no_mail == []


@pytest.mark.parametrize("trap", [{"website": "http://spam"}, {"t_ms": 500}])
def test_bots_get_normal_answer_nothing_stored(spaces, no_mail, trap):
    ids = spaces([ROOM])
    before = _q("SELECT count(*) FROM bo_suu_tap")[0][0]
    r = client.post("/briefs", json={**BRIEF, **trap, "items": _items(ids)})
    assert r.status_code == 201 and r.json()["lead_id"] is None and r.json()["ma_chia_se"] is None
    assert _q("SELECT count(*) FROM bo_suu_tap")[0][0] == before and no_mail == []


def test_briefs_and_contact_form_share_one_limit(spaces, no_mail):
    ids = spaces([ROOM])
    codes = [client.post("/leads", json={"ho_ten": "Lan", "so_dien_thoai": "0912345678", "t_ms": 8000}).status_code
             for _ in range(3)]
    codes += [client.post("/briefs", json={**BRIEF, "items": _items(ids)}).status_code for _ in range(3)]
    assert codes == [201] * 5 + [429]
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE nguon='form' AND so_dien_thoai='0912345678'")


def test_unknown_share_code():
    assert client.get("/collections/shared/khongcoMaNay123").status_code == 404
    assert client.get("/collections/shared/a").status_code == 422


def test_brief_profile_needs_both_consents(spaces, no_mail):
    ids = spaces([ROOM])
    pid = uuid.uuid4().hex
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
        c.execute("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri) VALUES (%s,'xem_khong_gian',%s,'{}')", (pid, ids[0]))
    try:
        yes = client.post("/briefs", json={**BRIEF, "items": _items(ids), "phien_id": pid, "gui_ho_so": True}).json()
        no = client.post("/briefs", json={**BRIEF, "items": _items(ids), "phien_id": pid}).json()
        assert _q("SELECT ho_so_hanh_vi IS NOT NULL FROM lead WHERE id=%s", yes["lead_id"])[0][0]
        assert _q("SELECT ho_so_hanh_vi IS NULL FROM lead WHERE id=%s", no["lead_id"])[0][0]
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM phien_truy_cap WHERE id=%s", (pid,))


# ── 3.3 notices ────────────────────────────────────────────────────────────────
def test_brief_emails_have_details_and_link(spaces, monkeypatch, no_mail):
    from test_leads import FakeSMTP
    ids = spaces(FIVE)
    r = client.post("/briefs", json={**BRIEF, "email": "lan@example.com", "items": _items(ids)}).json()
    monkeypatch.undo()  # real notify functions, fake SMTP
    FakeSMTP.sent = []
    monkeypatch.setenv("D3_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("D3_SALES_EMAIL", "sales@example.com")
    monkeypatch.setenv("D3_FRONTEND_URL", "http://localhost:8080/prj1/")
    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)
    notify.notify_new_lead(r["lead_id"])
    notify.confirm_to_visitor(r["lead_id"])
    sales, visitor = (m.get_content() for m in FakeSMTP.sent)
    link = f"http://localhost:8080/prj1/bo-suu-tap/xem/{r['ma_chia_se']}"
    assert "Bộ sưu tập (brief)" in sales and "Căn hộ / Chung cư" in sales and "70 m²" in sales
    assert "300 – 700 triệu" in sales and "Wabi-sabi 60% · tông Ấm · phòng khách" in sales and link in sales
    assert link in visitor and "Sở thích" not in visitor


# ── 3.4 GET /leads ─────────────────────────────────────────────────────────────
def test_leads_list_brief_items_and_filter(spaces, as_role, no_mail):
    ids = spaces([ROOM, ROOM])
    r = client.post("/briefs", json={**BRIEF, "items": _items(ids, {ids[1]: "đẹp"})}).json()
    sales = as_role("sales")
    row = next(x for x in client.get("/leads", params={"nguon": "brief"}, headers=sales).json() if x["id"] == r["lead_id"])
    assert row["ma_chia_se"] == r["ma_chia_se"] and [i["id"] for i in row["bo_suu_tap"]] == ids
    assert row["bo_suu_tap"][1]["ghi_chu"] == "đẹp" and row["request"]["ngan_sach"] == "300tr_700tr"
    assert {x["nguon"] for x in client.get("/leads", params={"nguon": "brief"}, headers=sales).json()} == {"brief"}
