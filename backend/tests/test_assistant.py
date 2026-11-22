"""RAG assistant skeleton. Needs Postgres with kb/sample.json loaded (python -m pipeline.assistant kb/sample.json)."""
import json

import psycopg

from conftest import client
from pipeline.assistant import load_kb, parse_request, unmapped_terms
from pipeline.store import DSN


def test_parse_request_without_diacritics():
    r = parse_request("Báo giá thiết kế phòng khách căn hộ 85,5m2 phong cách Japandi")
    assert r["project_type"] == "can_ho" and r["space_type"] == "phong_khach" and r["area_m2"] == 85.5
    assert r["design_style"] == "Japandi" and r["price_intent"] and not r["appointment_intent"]
    r = parse_request("toi muon dat lich hen tu van, phong cach tan co dien")
    assert r["appointment_intent"] and r["design_style"] == "Tan_co_dien" and not r["price_intent"]


def _leads():
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT count(*) FROM lead").fetchone()[0]


PRICE = {"kind": "price", "title": "TEST bảng giá thiết kế nội thất biệt thự",
         "match": "báo giá thiết kế nội thất biệt thự nhà phố giá bao nhiêu tính phí thế nào", "content": "Nội dung kiểm thử."}


def test_price_question_is_never_answered_with_a_price_but_still_creates_a_lead(tmp_path):
    # the site shows no prices (the owner's decision, Tùng 9399c77): even a live price entry is never said
    from pipeline.assistant import MONEY
    kb = tmp_path / "price.json"
    kb.write_text(json.dumps([PRICE], ensure_ascii=False), encoding="utf-8")
    load_kb(str(kb))
    before = _leads()
    try:
        r = client.post("/chat", json={"message": "Làm nội thất biệt thự tính phí thế nào?", "contact": "0900000000"}).json()
        assert all(s["title"] != PRICE["title"] for s in r["sources"]) and not MONEY.search(r["answer"])
        assert r["lead_id"] and _leads() == before + 1  # the architect calls back about the cost
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE id > 0 AND contact = '0900000000'")
            c.execute("DELETE FROM kb_chunk WHERE title = %s", (PRICE["title"],))


def test_off_topic_is_declined_without_lead_or_gap():
    q = "Giải giúp tôi phương trình x^2 - 5x + 6 = 0"
    try:
        r = client.post("/chat", json={"message": q, "contact": "0911111111"}).json()
        assert not r["answered"] and not r["sources"] and not r["images"] and r["lead_id"] is None and r.get("lac_de")
        assert "chỉ trả lời các câu hỏi về thiết kế" in r["answer"] and "chưa có thông tin" not in r["answer"]
        with psycopg.connect(DSN) as c:
            assert c.execute("SELECT count(*) FROM khoang_trong_tri_thuc WHERE cau_hoi = %s", (q,)).fetchone()[0] == 0
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE contact = '0911111111'")
            c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = %s", (q,))


def test_chat_images_only_published(drafts):
    """Chat shows published spaces only. Publishes three drafts for the test; the fixture puts them back."""
    q = {"message": "Bên bạn thiết kế phòng khách gồm những gì?"}
    ids = drafts(3, "space_type='phong_khach'")
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status='published' WHERE id = ANY(%s)", (ids,))
        published = {r[0] for r in c.execute("SELECT id FROM space WHERE review_status='published'")}
    try:
        imgs = client.post("/chat", json=q).json()["images"]
        assert imgs and {i["id"] for i in imgs} <= published
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE conversation @> '[{\"content\": \"%s\"}]'::jsonb" % q["message"])


def test_chat_validates_input():
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_hotspots_link_to_services(as_role):
    admin = as_role("admin")
    sid = client.get("/spaces", params={"space_type": "phong_khach", "limit": 1}, headers=admin).json()[0]["id"]
    objs = client.get(f"/spaces/{sid}", headers=admin).json()["hotspots"]["objects"]
    assert all("service" in o for o in objs)
    assert any(o["service"] == "Dịch vụ thiết kế phòng khách" for o in objs if o["label"] == "couch") or not any(o["label"] == "couch" for o in objs)


def test_leads_visible_to_sales_only(as_role):
    try:
        lead_id = client.post("/chat", json={"message": "Cách nấu phở bò ngon", "contact": "0922222222"}).json()["lead_id"]
        assert client.get("/leads").status_code == 401
        assert client.get("/leads", headers=as_role("visitor")).status_code == 403
        rows = client.get("/leads", headers=as_role("sales")).json()
        assert any(r["id"] == lead_id and r["intent"] == "handoff" for r in rows)
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE contact = '0922222222'")
            c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = 'Cách nấu phở bò ngon'")


def test_validate_kb():
    from pipeline.assistant import validate_kb
    ok = {"kind": "faq", "title": "A", "match": "m", "content": "c"}
    assert validate_kb([ok]) == []
    errs = validate_kb([ok, ok, {"kind": "x", "title": "B", "match": "", "content": "c"}])
    assert any("duplicate" in e for e in errs) and any("'match'" in e for e in errs) and any("kind must" in e for e in errs)


# ── knowledge gaps (discover-taxonomy-dimensions 1.2) ──────────────────────────
def test_unmapped_terms_skip_taxonomy_words_and_stopwords():
    assert unmapped_terms("Phòng khách phong cách Indochine giá bao nhiêu?") == []
    assert unmapped_terms("Nhà mình muốn phòng khách nhiều cây xanh có giếng trời") == ["cay", "xanh", "gieng", "troi"]


def test_unanswered_question_is_logged_as_a_gap():
    q = "Thiết kế phòng khách kiểu biophilic có giếng trời"
    try:
        r = client.post("/chat", json={"message": q}).json()
        assert not r["answered"] and r["lead_id"]
        with psycopg.connect(DSN) as c:
            terms, best = c.execute("SELECT tu_chua_khop, diem_cao_nhat FROM khoang_trong_tri_thuc WHERE cau_hoi=%s", (q,)).fetchone()
        assert "biophilic" in terms and "gieng" in terms and best is not None
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE conversation @> %s::jsonb", (json.dumps([{"content": q}]),))
            c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = %s", (q,))


def test_answered_question_logs_no_gap():
    with psycopg.connect(DSN) as c:
        before = c.execute("SELECT count(*) FROM khoang_trong_tri_thuc").fetchone()[0]
    r = client.post("/chat", json={"message": "D3 Studio có thiết kế phòng khách không?"}).json()
    with psycopg.connect(DSN) as c:
        assert r["answered"] and c.execute("SELECT count(*) FROM khoang_trong_tri_thuc").fetchone()[0] == before


# ── small talk: greetings, thanks, goodbyes are answered here, never handed off ──────────────────────────────────
import pytest  # noqa: E402

from pipeline.assistant import small_talk  # noqa: E402


@pytest.mark.parametrize("msg,kind", [
    ("xin chào", "chao"), ("Xin chào shop!", "chao"), ("hello", "chao"), ("Hi ad", "chao"), ("chào bạn ạ", "chao"),
    ("alo", "chao"), ("Good morning D3 Studio", "chao"),
    ("cảm ơn", "cam_on"), ("Cảm ơn bạn nhiều nhé!", "cam_on"), ("thanks", "cam_on"), ("thank you", "cam_on"),
    ("chào, cảm ơn nhé", "cam_on"),
    ("tạm biệt", "tam_biet"), ("bye", "tam_biet"), ("Hẹn gặp lại!", "tam_biet"),
])
def test_small_talk_is_recognised(msg, kind):
    assert small_talk(msg) == kind


@pytest.mark.parametrize("msg", [
    "chào shop, mình muốn thiết kế phòng khách Japandi", "xin báo giá phòng ngủ", "hello, chi phí bao nhiêu?",
    "cảm ơn, cho mình hỏi thêm về quy trình", "", "   ", "xin", "ok",
])
def test_real_questions_are_not_small_talk(msg):
    assert small_talk(msg) is None


def test_greeting_makes_no_lead_and_no_gap():
    with psycopg.connect(DSN) as c:
        leads0 = c.execute("SELECT count(*) FROM lead").fetchone()[0]
        gaps0 = c.execute("SELECT count(*) FROM khoang_trong_tri_thuc").fetchone()[0]
    r = client.post("/chat", json={"message": "Xin chào!"}).json()
    assert r["answered"] is True and r["answer"].startswith("Xin chào!") and r["lead_id"] is None
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT count(*) FROM lead").fetchone()[0] == leads0
        assert c.execute("SELECT count(*) FROM khoang_trong_tri_thuc").fetchone()[0] == gaps0


# ── assistant-project-results: examples are projects, ranked by the collected request ──────────────────────────
def test_kb_answer_returns_ranked_projects_of_published_photos(drafts):
    q = {"message": "Bên bạn thiết kế phòng khách gồm những gì?"}
    ids = drafts(3, "space_type='phong_khach'")
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status='published' WHERE id = ANY(%s)", (ids,))
        published = {r[0] for r in c.execute("SELECT id FROM space WHERE review_status='published'")}
    try:
        r = client.post("/chat", json=q).json()
        slugs = [p["slug"] for p in r["projects"]]  # project-catalog: one card per catalog project
        assert 1 <= len(slugs) <= 3 and len(set(slugs)) == len(slugs) and all(p["ten"] for p in r["projects"])
        photos = [a for p in r["projects"] for a in p["anh"]]
        assert all(1 <= len(p["anh"]) <= 2 for p in r["projects"]) and {a["id"] for a in photos} <= published
        assert r["images"] == photos  # older clients see the cards' photos
        assert any(k["chieu"] == "khong_gian" for k in r["projects"][0]["khop"])  # the room asked for is matched
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE conversation @> '[{\"content\": \"%s\"}]'::jsonb" % q["message"])


def test_small_talk_and_handoff_have_no_projects():
    assert client.post("/chat", json={"message": "xin chào"}).json()["projects"] == []


# ── seq-3 RAG: a matched entry is used to answer the question itself, not pasted as it is ──────────────────────────
def test_kb_answer_is_drafted_from_the_entries_and_falls_back_to_the_entry(monkeypatch):
    from pipeline import assistant, vertex
    q = "Phong cách Japandi hợp với căn hộ nhỏ không?"
    hits = assistant.retrieve(q)
    assert hits and hits[0][4] >= assistant.MIN_SCORE, "needs the Japandi sample entry (kb/sample.json)"
    seen = {}

    def fake(parts, **kw):
        seen["prompt"] = parts[0]["text"]
        return {"answerable": True, "answer": "Có, Japandi hợp với căn hộ nhỏ.", "used": [hits[0][0]]}, {}
    monkeypatch.setattr(vertex, "available", lambda: True)
    monkeypatch.setattr(vertex, "generate", fake)
    r = assistant.respond(q)
    assert r["answered"] and "Japandi hợp với căn hộ nhỏ" in r["answer"] and r["answer"] != hits[0][3]
    assert hits[0][2] in seen["prompt"] and q in seen["prompt"]  # the entry and the question went to the model
    assert r["answer"].startswith(assistant.SAMPLE) == hits[0][3].startswith(assistant.SAMPLE)  # sample stays marked
    assert [s["id"] for s in r["sources"]] == [hits[0][0]]  # only the entry the answer used is named as a source

    monkeypatch.setattr(vertex, "generate", lambda parts, **kw: ({"answerable": False}, {}))
    assert assistant.respond(q)["answer"] == hits[0][3]  # the model can't: the best entry, as before

    def broken(parts, **kw):
        raise TimeoutError("vertex down")
    monkeypatch.setattr(vertex, "generate", broken)
    assert assistant.respond(q)["answer"] == hits[0][3]


def test_price_question_the_entries_cannot_answer_says_prices_are_given_by_an_architect(monkeypatch):
    from pipeline import assistant, vertex
    monkeypatch.setattr(vertex, "available", lambda: True)
    monkeypatch.setattr(vertex, "generate", lambda parts, **kw: ({"answerable": False}, {}))
    monkeypatch.setattr(assistant.leads, "create_lead", lambda *a, **k: 1)
    monkeypatch.setattr(assistant, "retrieve", lambda q, k=3: [(1, "faq", "Thời gian thi công", "Thi công 45 ngày.", 0.95)])
    r = assistant.respond("bao nhiêu tiền?")
    assert r["answer"].startswith(assistant.PRICE_REPLY) and "Thi công 45 ngày" not in r["answer"]
    assert "để lại số điện thoại" in r["answer"] and r["lead_id"] == 1  # still the call-back offer and a lead


def test_a_faq_answer_gets_no_project_cards_even_when_it_names_a_project_type(monkeypatch):
    from pipeline import assistant
    monkeypatch.setattr(assistant.leads, "create_lead", lambda *a, **k: None)
    r = assistant.respond("Thiết kế căn hộ mất bao lâu?")  # names "căn hộ", answered by the timing FAQ
    assert r["answered"] and r["request"]["project_type"] == "can_ho" and r["sources"][0]["kind"] == "faq"
    assert r["projects"] == [] and r["images"] == []


def test_the_call_back_line_is_not_added_when_the_answer_already_asks_for_a_contact(monkeypatch):
    from pipeline import assistant, vertex
    monkeypatch.setattr(vertex, "available", lambda: True)
    monkeypatch.setattr(assistant.leads, "create_lead", lambda *a, **k: 1)
    entry = (1, "faq", "Đặt lịch tư vấn", "Buổi tư vấn kéo dài 45 phút. Để lại số điện thoại để kiến trúc sư xác nhận lịch.", 0.95)
    monkeypatch.setattr(assistant, "retrieve", lambda q, k=3: [entry])
    monkeypatch.setattr(vertex, "generate", lambda parts, **kw: ({"answerable": False}, {}))
    r = assistant.respond("Tôi muốn đặt lịch hẹn gặp kiến trúc sư")
    assert r["answer"] == entry[3] and r["lead_id"] == 1  # asked once, by the entry itself
    monkeypatch.setattr(assistant, "retrieve", lambda q, k=3: [entry[:3] + ("Buổi tư vấn kéo dài 45 phút.", 0.95)])
    assert "để lại số điện thoại hoặc email" in assistant.respond("Tôi muốn đặt lịch hẹn gặp kiến trúc sư")["answer"]
