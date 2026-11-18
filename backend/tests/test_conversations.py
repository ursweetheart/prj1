"""Chat conversations (change chat-history). The language model is switched off (vertex.available -> False), so an
unanswered question takes the fallback path; every conversation and lead a test makes is removed afterwards."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import assistant, conversations as cv
from pipeline.assistant import parse_request
from pipeline.store import DSN


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def chat(monkeypatch):
    """chat(message, hid=None, **body) -> response json; conversations, leads and gaps removed afterwards."""
    monkeypatch.setattr(assistant.vertex, "available", lambda: False)
    made, asked, leads = set(), [], []

    def send(message, hid=None, **body):
        r = client.post("/chat", json={"message": message, **({"hoi_thoai_id": hid} if hid else {}), **body})
        assert r.status_code == 200, r.text
        out = r.json()
        made.add(out["hoi_thoai_id"])
        asked.append(message)
        if out.get("lead_id"):  # kept by id: deleting a conversation clears the lead's link to it
            leads.append(out["lead_id"])
        return out

    yield send
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id = ANY(%s) OR hoi_thoai_id = ANY(%s)", (leads, list(made)))
        c.execute("DELETE FROM hoi_thoai WHERE id = ANY(%s)", (list(made),))
        c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = ANY(%s)", (asked,))


@pytest.fixture
def session():
    pid = "t" + uuid.uuid4().hex
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
    yield pid
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM phien_truy_cap WHERE id = %s", (pid,))


# ── 1.2 module ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text, want", [
    ("gọi em số 0912 345 678 nhé", "gọi em số [số điện thoại] nhé"),
    ("0912.345.678", "[số điện thoại]"),
    ("+84 912 345 678 ạ", "[số điện thoại] ạ"),
    ("mail a.b@c.vn giúp em", "mail [email] giúp em"),
    ("chung cư 70m2, 3 phòng ngủ, năm 2025", "chung cư 70m2, 3 phòng ngủ, năm 2025"),
    ("mã 01234567890123", "mã 01234567890123"),
])
def test_mask(text, want):
    assert cv.mask(text) == want


def test_merge_keeps_old_values_unless_replaced():
    old = {"project_type": "chung_cu", "area_m2": 70.0}
    assert cv.merge(old, {"project_type": None, "design_style": "Wabi_sabi", "price_intent": True}) == \
        {"project_type": "chung_cu", "area_m2": 70.0, "design_style": "Wabi_sabi"}
    assert cv.merge(old, {"project_type": "nha_pho"})["project_type"] == "nha_pho"


def test_start_or_get_new_ids_and_consent_link(session):
    made = []
    try:
        with psycopg.connect(DSN) as c:
            for bad in (None, "nope", "f" * 32, "../" + "a" * 29):
                hid, rb, turns = cv.start_or_get(c, bad)
                made.append(hid)
                assert cv.valid(hid) and hid != bad and rb == {} and turns == []
            anon, _, _ = cv.start_or_get(c, None, None)  # no consent: no session id is sent
            linked, _, _ = cv.start_or_get(c, None, session)
            fresh_pid = "t" + uuid.uuid4().hex  # consented, but no tracked view yet: the session row is created
            fresh, _, _ = cv.start_or_get(c, None, fresh_pid)
            made += [anon, linked, fresh]
        rows = dict(_q("SELECT id, phien_id FROM hoi_thoai WHERE id = ANY(%s)", made))
        assert rows[anon] is None and rows[linked] == session and rows[fresh] == fresh_pid
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM hoi_thoai WHERE id = ANY(%s)", (made,))
            c.execute("DELETE FROM phien_truy_cap WHERE id = %s", (locals().get("fresh_pid"),))


def test_purge_after_90_days():
    old, recent = uuid.uuid4().hex, uuid.uuid4().hex
    with psycopg.connect(DSN) as c:
        for hid, days in ((old, 91), (recent, 89)):
            c.execute("INSERT INTO hoi_thoai (id, cap_nhat) VALUES (%s, now() - make_interval(days => %s))", (hid, days))
            c.execute("INSERT INTO tin_nhan (hoi_thoai_id, vai_tro, noi_dung) VALUES (%s, 'khach', 'x')", (hid,))
        cv.purge(c)
    try:
        assert _q("SELECT id FROM hoi_thoai WHERE id = ANY(%s)", [old, recent]) == [(recent,)]
        assert _q("SELECT count(*) FROM tin_nhan WHERE hoi_thoai_id = %s", old)[0][0] == 0
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM hoi_thoai WHERE id = %s", (recent,))


# ── 1.3 chat ────────────────────────────────────────────────────────────────────
def test_two_questions_one_anonymous_conversation(chat):
    a = chat("Cách nấu phở bò ngon")
    b = chat("Còn bún chả thì sao", a["hoi_thoai_id"])
    hid = a["hoi_thoai_id"]
    assert b["hoi_thoai_id"] == hid
    (phien, n, unanswered, handed), = _q("SELECT phien_id, so_tin_nhan, chua_tra_loi, da_chuyen_nguoi_that FROM hoi_thoai "
                                         "WHERE id = %s", hid)
    assert (phien, n, unanswered, handed) == (None, 4, 2, True)
    roles = [r for (r,) in _q("SELECT vai_tro FROM tin_nhan WHERE hoi_thoai_id = %s ORDER BY id", hid)]
    assert roles == ["khach", "tro_ly", "khach", "tro_ly"]
    assert _q("SELECT count(*) FROM lead WHERE hoi_thoai_id = %s", hid)[0][0] == 2


def test_consented_session_is_linked(chat, session):
    hid = chat("Cách nấu phở bò ngon", phien_id=session)["hoi_thoai_id"]
    assert _q("SELECT phien_id FROM hoi_thoai WHERE id = %s", hid)[0][0] == session


def test_constraints_carry_into_the_lead(chat):
    first = chat("Nhà em là chung cư 70m2")
    second = chat("Muốn làm phong cách wabi-sabi thì sao", first["hoi_thoai_id"])
    want = {k: v for k, v in parse_request("chung cư 70m2 wabi-sabi").items()
            if k in ("project_type", "area_m2", "design_style")}
    assert all(want.values()), want  # the taxonomy knows all three words
    req = _q("SELECT request FROM lead WHERE id = %s", second["lead_id"])[0][0]
    assert {k: req[k] for k in want} == want
    assert {k: second["rang_buoc"][k] for k in want} == want
    stored = _q("SELECT rang_buoc FROM hoi_thoai WHERE id = %s", first["hoi_thoai_id"])[0][0]
    assert {k: stored[k] for k in want} == want


def test_later_value_replaces_earlier(chat):
    first = chat("Nhà em là chung cư")
    second = chat("À không, nhà phố", first["hoi_thoai_id"])
    assert second["rang_buoc"]["project_type"] == parse_request("nhà phố")["project_type"] != \
        parse_request("chung cư")["project_type"]


def test_contact_masked_in_conversation_not_in_lead(chat):
    out = chat("Gọi em số 0912 345 678 nhé, nấu phở thế nào", contact="0912345678")
    stored = _q("SELECT noi_dung FROM tin_nhan WHERE hoi_thoai_id = %s AND vai_tro = 'khach'", out["hoi_thoai_id"])[0][0]
    assert "0912" not in stored and "[số điện thoại]" in stored
    contact, conv = _q("SELECT contact, conversation FROM lead WHERE id = %s", out["lead_id"])[0]
    assert contact == "0912345678" and "0912 345 678" in conv[-1]["content"]


def test_read_delete_and_bad_ids(chat):
    hid = chat("Cách nấu phở bò ngon, số em 0912345678")["hoi_thoai_id"]
    r = client.get(f"/chat/{hid}").json()
    assert [m["vai_tro"] for m in r["tin_nhan"]] == ["khach", "tro_ly"]
    assert "[số điện thoại]" in r["tin_nhan"][0]["noi_dung"] and "diem_cao_nhat" not in r["tin_nhan"][1]
    assert client.delete(f"/chat/{hid}").status_code == 204
    assert client.get(f"/chat/{hid}").status_code == 404
    assert client.delete(f"/chat/{hid}").status_code == 204
    assert client.get("/chat/not-an-id").status_code == 404


def test_client_history_ignored_once_turns_are_stored(chat, monkeypatch):
    seen = []
    real = assistant.respond

    def spy(message, history=None, *a, **kw):
        seen.append(history)
        return real(message, history, *a, **kw)
    monkeypatch.setattr("api.respond", spy)
    hid = chat("Cách nấu phở bò ngon")["hoi_thoai_id"]
    chat("Còn bún chả", hid, history=[{"role": "user", "content": "BỊA RA"}])
    assert seen[1][0]["content"] == "Cách nấu phở bò ngon" and all(m["content"] != "BỊA RA" for m in seen[1])


# ── 1.4 staff ───────────────────────────────────────────────────────────────────
def test_staff_roles(as_role):
    for role in ("content", "sales", "lead_architect", "admin"):
        assert client.get("/conversations", headers=as_role(role)).status_code == 200
    for role in ("visitor", "architect"):
        h = as_role(role)
        assert client.get("/conversations", headers=h).status_code == 403
        assert client.get("/conversations/" + "a" * 32, headers=h).status_code == 403
    assert client.get("/conversations").status_code == 401


def test_staff_filters_and_detail(chat, as_role):
    h = as_role("content")
    unanswered = chat("Cách nấu phở bò ngon, gọi 0912 345 678")["hoi_thoai_id"]
    # an answered-looking conversation without a lead: written directly, so no model or knowledge base is needed
    quiet = uuid.uuid4().hex
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO hoi_thoai (id, so_tin_nhan) VALUES (%s, 2)", (quiet,))
        c.execute("INSERT INTO tin_nhan (hoi_thoai_id, vai_tro, noi_dung) VALUES (%s, 'khach', 'Có làm phòng khách không')", (quiet,))
    try:
        ids = lambda loc: {i["id"] for i in client.get("/conversations", params={"loc": loc, "days": 7}, headers=h).json()["items"]}  # noqa: E731
        assert {unanswered, quiet} <= ids("tat_ca")
        assert unanswered in ids("chua_tra_loi") and quiet not in ids("chua_tra_loi")
        assert unanswered in ids("lead") and quiet not in ids("lead")
        body = client.get("/conversations", headers=h).text
        assert "0912" not in body and "phien_id" not in body
        d = client.get(f"/conversations/{unanswered}", headers=h).json()
        assert d["lead_id"] and d["da_chuyen_nguoi_that"] and d["tin_nhan"][1]["tra_loi_duoc"] is False
        assert "diem_cao_nhat" in d["tin_nhan"][1] and "nguon" in d["tin_nhan"][1]
        assert client.get("/conversations", params={"days": 10}, headers=h).status_code == 422
        assert client.get("/conversations", params={"loc": "x"}, headers=h).status_code == 422
        assert client.get("/conversations/" + "0" * 32, headers=h).status_code == 404
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM hoi_thoai WHERE id = %s", (quiet,))
