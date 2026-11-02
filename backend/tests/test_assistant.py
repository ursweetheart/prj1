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


def test_answer_has_sources_and_creates_price_lead(tmp_path):
    # the knowledge base holds no price list until D3 Studio provides one: load a throw-away chunk for this test
    kb = tmp_path / "price.json"
    kb.write_text(json.dumps([PRICE], ensure_ascii=False), encoding="utf-8")
    load_kb(str(kb))
    before = _leads()
    try:
        r = client.post("/chat", json={"message": "Làm nội thất biệt thự tính phí thế nào?", "contact": "0900000000"}).json()
        assert r["answered"] and r["sources"][0]["title"] == PRICE["title"]
        assert r["lead_id"] and _leads() == before + 1
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE id > 0 AND contact = '0900000000'")
            c.execute("DELETE FROM kb_chunk WHERE title = %s", (PRICE["title"],))


def test_off_topic_is_refused_and_handed_off():
    try:
        r = client.post("/chat", json={"message": "Cách nấu phở bò ngon", "contact": "0911111111"}).json()
        assert not r["answered"] and not r["sources"] and not r["images"] and "chưa có thông tin" in r["answer"]
        with psycopg.connect(DSN) as c:
            assert c.execute("SELECT intent FROM lead WHERE id=%s", (r["lead_id"],)).fetchone()[0] == "handoff"
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE contact = '0911111111'")
            c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = 'Cách nấu phở bò ngon'")


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
