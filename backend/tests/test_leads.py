"""Lead intake (change lead-intake): POST /leads, consented behaviour profile, notifications, GET /leads.
Needs the DB with at least 4 published spaces."""
import logging
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import leads, notify
from pipeline.store import DSN

FORM = {"ho_ten": "Lan", "so_dien_thoai": "0912345678", "loi_nhan": "Căn hộ 70m2", "trang": "/du-an/du-an-mau-01",
        "du_an": "du-an-mau-01", "t_ms": 8000}


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def cleanup():
    """Delete the leads and sessions a test made."""
    made = {"leads": [], "sessions": []}
    yield made
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id = ANY(%s) OR so_dien_thoai IN ('0912345678', '0987654321')",
                  ([i for i in made["leads"] if i],))
        c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (made["sessions"],))  # cascades to su_kien


@pytest.fixture
def no_mail(monkeypatch):
    """Notifications recorded instead of sent; SMTP unset."""
    for k in ("D3_SMTP_HOST", "D3_SALES_EMAIL"):
        monkeypatch.delenv(k, raising=False)
    calls = []
    monkeypatch.setattr(notify, "notify_new_lead", lambda i: calls.append(("sales", i)))
    monkeypatch.setattr(notify, "confirm_to_visitor", lambda i: calls.append(("visitor", i)))
    return calls


def _session(cleanup, views=None):
    """A consented session with views [(space_id, [gia_tri...]), ...] in viewing order (last = newest)."""
    pid = uuid.uuid4().hex
    cleanup["sessions"].append(pid)
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
        for n, (sid, vals) in enumerate(views or []):
            c.execute("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri, created_at) "
                      "VALUES (%s, 'xem_khong_gian', %s, %s, now() - make_interval(secs => %s))",
                      (pid, sid, vals, len(views) - n))
    return pid


def _four_views(cleanup):
    ids = [r[0] for r in _q("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 4")]
    wabi = ["phong_cach:Wabi_sabi", "khong_gian:phong_khach"]
    views = [(ids[0], wabi), (ids[1], wabi), (ids[2], ["phong_cach:Japandi"]), (ids[3], wabi)]
    return _session(cleanup, views), ids


# ── 2.1 profile ────────────────────────────────────────────────────────────────
def test_profile_lists_newest_spaces_and_top_values(cleanup):
    pid, ids = _four_views(cleanup)
    p = leads.behaviour_profile(pid)
    assert [s["id"] for s in p["spaces"]] == ids[::-1]  # newest first
    assert p["views"] == 4
    assert p["top"][0]["gia_tri"] == "phong_cach:Wabi_sabi" and p["top"][0]["so_lan"] == 3
    assert p["top"][0]["ten"] == "Wabi-sabi"  # display name from the taxonomy


def test_profile_summary_line(cleanup):
    pid, _ = _four_views(cleanup)
    assert leads.profile_summary(leads.behaviour_profile(pid)) == "Wabi-sabi 75% · phòng khách · 4 không gian"
    assert leads.profile_summary(None) == ""


def test_profile_caps_spaces_at_12(cleanup):
    ids = [r[0] for r in _q("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 14")]
    pid = _session(cleanup, [(i, []) for i in ids])
    assert len(leads.behaviour_profile(pid)["spaces"]) == min(12, len(ids))


# ── 2.2 consent rule ───────────────────────────────────────────────────────────
def test_profile_only_with_ticked_box_and_consented_session(cleanup):
    pid, _ = _four_views(cleanup)
    with_box = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678", phien_id=pid, gui_ho_so=True)
    no_box = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678", phien_id=pid, gui_ho_so=False)
    declined = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678", phien_id=uuid.uuid4().hex,
                                 gui_ho_so=True)  # no phien_truy_cap row: the visitor never consented
    cleanup["leads"] += [with_box, no_box, declined]
    rows = dict((r[0], r[1:]) for r in _q("SELECT id, phien_id, ho_so_hanh_vi FROM lead WHERE id = ANY(%s)",
                                          [with_box, no_box, declined]))
    assert rows[with_box][0] == pid and rows[with_box][1]["views"] == 4
    assert rows[no_box] == (None, None)
    assert rows[declined] == (None, None)


def test_unknown_source_is_refused():
    with pytest.raises(ValueError):
        leads.create_lead("fax")


# ── 2.3 notifications ──────────────────────────────────────────────────────────
class FakeSMTP:
    sent = []

    def __init__(self, *a, **kw): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): pass
    def login(self, *a): pass
    def send_message(self, msg): FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setenv("D3_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("D3_SALES_EMAIL", "sales@example.com")
    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP.sent


def test_sales_email_has_contact_context_and_summary(cleanup, smtp):
    pid, _ = _four_views(cleanup)
    lid = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678", email="lan@example.com",
                            ngu_canh={"trang": "/du-an/du-an-mau-01", "du_an": "du-an-mau-01"}, phien_id=pid, gui_ho_so=True)
    cleanup["leads"].append(lid)
    notify.notify_new_lead(lid)
    notify.confirm_to_visitor(lid)
    sales, visitor = smtp
    body = sales.get_content()
    assert sales["To"] == "sales@example.com"
    assert "0912345678" in body and "du-an-mau-01" in body and "Wabi-sabi 75%" in body
    assert visitor["To"] == "lan@example.com" and "Wabi" not in visitor.get_content()


def test_no_visitor_mail_without_email(cleanup, smtp):
    lid = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678")
    cleanup["leads"].append(lid)
    notify.confirm_to_visitor(lid)
    assert smtp == []


def test_mail_failure_is_logged_not_raised(cleanup, smtp, monkeypatch, caplog):
    class Down(FakeSMTP):
        def send_message(self, msg): raise OSError("connection refused")
    monkeypatch.setattr(notify.smtplib, "SMTP", Down)
    lid = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678")
    cleanup["leads"].append(lid)
    with caplog.at_level(logging.ERROR, logger="d3.leads"):
        notify.notify_new_lead(lid)  # must not raise
    assert f"lead {lid}" in caplog.text


def test_without_smtp_only_a_log_line_without_personal_data(cleanup, monkeypatch, caplog):
    monkeypatch.delenv("D3_SMTP_HOST", raising=False)
    lid = leads.create_lead("form", ho_ten="Lan", so_dien_thoai="0912345678", email="lan@example.com")
    cleanup["leads"].append(lid)
    with caplog.at_level(logging.INFO, logger="d3.leads"):
        notify.notify_new_lead(lid)
    assert f"lead {lid}" in caplog.text
    assert "0912345678" not in caplog.text and "lan@example.com" not in caplog.text


# ── 3.1 POST /leads ────────────────────────────────────────────────────────────
def test_valid_form_stores_context_and_notifies(cleanup, no_mail):
    r = client.post("/leads", json=FORM)
    assert r.status_code == 201 and "0912345678" in r.json()["message"]
    lid = r.json()["lead_id"]
    cleanup["leads"].append(lid)
    row = _q("SELECT nguon, ho_ten, so_dien_thoai, email, loi_nhan, ngu_canh FROM lead WHERE id=%s", lid)[0]
    assert row == ("form", "Lan", "0912345678", None, "Căn hộ 70m2", {"trang": "/du-an/du-an-mau-01", "du_an": "du-an-mau-01"})
    assert no_mail == [("sales", lid), ("visitor", lid)]


def test_phone_with_spaces_and_country_code_is_normalised(cleanup, no_mail):
    lid = client.post("/leads", json={**FORM, "so_dien_thoai": "+84 912 345 678"}).json()["lead_id"]
    cleanup["leads"].append(lid)
    assert _q("SELECT so_dien_thoai FROM lead WHERE id=%s", lid)[0][0] == "0912345678"


@pytest.mark.parametrize("field, value", [("so_dien_thoai", "12345"), ("ho_ten", "   "), ("email", "lan@"),
                                          ("loi_nhan", "x" * 1001)])
def test_invalid_field_is_named_and_nothing_stored(cleanup, no_mail, field, value):
    before = _q("SELECT count(*) FROM lead")[0][0]
    r = client.post("/leads", json={**FORM, field: value})
    assert r.status_code == 422 and any(e["loc"][-1] == field for e in r.json()["detail"])
    assert _q("SELECT count(*) FROM lead")[0][0] == before and no_mail == []


@pytest.mark.parametrize("trap", [{"website": "http://spam.example"}, {"t_ms": 900}])
def test_bots_get_the_same_answer_but_nothing_happens(cleanup, no_mail, trap):
    before = _q("SELECT count(*) FROM lead")[0][0]
    r = client.post("/leads", json={**FORM, **trap})
    assert r.status_code == 201 and r.json()["lead_id"] is None
    assert _q("SELECT count(*) FROM lead")[0][0] == before and no_mail == []


def test_sixth_submission_in_ten_minutes_is_limited(cleanup, no_mail):
    codes = []
    for _ in range(6):
        r = client.post("/leads", json=FORM)
        codes.append(r.status_code)
        if r.status_code == 201:
            cleanup["leads"].append(r.json()["lead_id"])
    assert codes == [201] * 5 + [429] and int(r.headers["Retry-After"]) > 0


def test_form_profile_needs_the_box(cleanup, no_mail):
    pid, _ = _four_views(cleanup)
    yes = client.post("/leads", json={**FORM, "phien_id": pid, "gui_ho_so": True}).json()["lead_id"]
    no = client.post("/leads", json={**FORM, "phien_id": pid}).json()["lead_id"]
    cleanup["leads"] += [yes, no]
    assert _q("SELECT ho_so_hanh_vi IS NOT NULL FROM lead WHERE id=%s", yes)[0][0]
    assert _q("SELECT ho_so_hanh_vi IS NULL AND phien_id IS NULL FROM lead WHERE id=%s", no)[0][0]


# ── 3.2 chat goes through the intake ───────────────────────────────────────────
def test_chat_handoff_with_consent_has_source_and_profile(cleanup, monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "notify_new_lead", lambda i: sent.append(i))
    pid, _ = _four_views(cleanup)
    r = client.post("/chat", json={"message": "Cách nấu phở bò ngon", "contact": "0987654321",
                                   "phien_id": pid, "gui_ho_so": True}).json()
    lid = r["lead_id"]
    cleanup["leads"].append(lid)
    nguon, intent, conv, prof = _q("SELECT nguon, intent, conversation, ho_so_hanh_vi FROM lead WHERE id=%s", lid)[0]
    assert (nguon, intent) == ("chat", "handoff") and conv[-1]["content"] == "Cách nấu phở bò ngon"
    assert prof["views"] == 4 and sent == [lid]


# ── 3.3 GET /leads ─────────────────────────────────────────────────────────────
def test_list_has_every_source_and_filters(cleanup, no_mail, as_role):
    form = client.post("/leads", json=FORM).json()["lead_id"]
    chat = leads.create_lead("chat", intent="price", contact="0987654321", conversation=[])
    cleanup["leads"] += [form, chat]
    sales = as_role("sales")
    rows = client.get("/leads", headers=sales).json()
    assert [r["id"] for r in rows[:2]] == [chat, form]  # newest first
    assert rows[1]["ho_ten"] == "Lan" and rows[1]["ngu_canh"]["du_an"] == "du-an-mau-01" and "tom_tat" in rows[1]
    only_form = client.get("/leads", params={"nguon": "form"}, headers=sales).json()
    assert {r["nguon"] for r in only_form} == {"form"} and form in [r["id"] for r in only_form]
    assert client.get("/leads").status_code == 401


def test_summary_keeps_room_type_when_ties_fill_the_top(cleanup):
    ids = [r[0] for r in _q("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 3")]
    common = ["phong_cach:Indochine", "tong_mau:dark", "vat_lieu:go", "vat_lieu:may_tre", "bo_cuc_cong_nang:phong_rieng_biet"]
    pid = _session(cleanup, [(ids[0], common + ["khong_gian:phong_ngu_master"]),
                             (ids[1], common + ["khong_gian:phong_ngu_master"]), (ids[2], common + ["khong_gian:khac"])])
    p = leads.behaviour_profile(pid)
    assert len(p["top"]) == 6  # 5 tied values + the leading room type
    assert leads.profile_summary(p) == "Indochine 100% · phòng ngủ master · 3 không gian"


def test_summary_never_names_khac_in_any_case(cleanup):
    ids = [r[0] for r in _q("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 2")]
    pid = _session(cleanup, [(i, ["phong_cach:Khac", "khong_gian:khac"]) for i in ids])
    assert leads.profile_summary(leads.behaviour_profile(pid)) == "2 không gian"
