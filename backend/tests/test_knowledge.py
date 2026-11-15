"""Assistant knowledge admin (change assistant-knowledge-admin). Throw-away entries titled 'test_kn …' and questions
starting 'test_kn'; the live sample entries are only touched where a test says so, and put back."""
import json

import psycopg
import pytest
from psycopg.rows import dict_row

from conftest import client
from pipeline import assistant, knowledge as kn
from pipeline.store import DSN

CONTENT = {"id": None, "role": "content", "email": "content@example.com"}
LEAD = {"id": None, "role": "lead_architect", "email": "lead@example.com"}


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


def _db():
    return psycopg.connect(DSN, row_factory=dict_row)  # what the API passes


@pytest.fixture(autouse=True)
def cleanup():
    yield
    with psycopg.connect(DSN) as c:
        ids = [r[0] for r in c.execute("SELECT id FROM kb_chunk WHERE title LIKE 'test_kn%%'").fetchall()]
        c.execute("DELETE FROM nhat_ky_tri_thuc WHERE kb_chunk_id = ANY(%s) OR (kb_chunk_id IS NULL AND sau::text LIKE '%%test_kn%%')", (ids,))
        c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi ILIKE 'test_kn%%' OR kb_chunk_id = ANY(%s)", (ids,))
        c.execute("DELETE FROM kb_chunk WHERE id = ANY(%s)", (ids,))
        c.execute("DELETE FROM lead WHERE contact = '0922222222'")


def _new(conn, user=CONTENT, kind="faq", title="test_kn chính sách đổi trả", phrases="chính sách đổi trả hàng nội thất",
         content="Đổi trả trong 7 ngày nếu lỗi do nhà sản xuất.", **kw):
    return kn.create(conn, user, kind, title, phrases, content, **kw)


# ── 1.1 loading and retrieval ──────────────────────────────────────────────────
def test_load_marks_ai_drafts_and_keeps_status(tmp_path):
    f = tmp_path / "kb.json"
    live = {"kind": "faq", "title": "test_kn mục sống", "match": "test kn mục sống", "content": "Nội dung."}
    draft = {"kind": "project", "title": "test_kn bản nháp AI", "match": "test kn nháp", "content": assistant.AI_MARK + " Mô tả."}
    f.write_text(json.dumps([live, draft], ensure_ascii=False), encoding="utf-8")
    assistant.load_kb(str(f))
    rows = dict((t, (s, n, m)) for t, s, n, m in _q("SELECT title, trang_thai, nguon, cum_tu_khop FROM kb_chunk WHERE title LIKE 'test_kn%%'"))
    assert rows["test_kn mục sống"] == ("dang_dung", "tep", "test kn mục sống")
    assert rows["test_kn bản nháp AI"][:2] == ("cho_duyet", "ai")
    assert "test_kn bản nháp AI" not in [h[2] for h in assistant.retrieve("test kn nháp", k=19)]
    with psycopg.connect(DSN) as c:  # someone switches the live one off; a re-load must not switch it back on
        c.execute("UPDATE kb_chunk SET trang_thai = 'tat' WHERE title = 'test_kn mục sống'")
    assistant.load_kb(str(f))
    assert _q("SELECT trang_thai FROM kb_chunk WHERE title = 'test_kn mục sống'")[0][0] == "tat"
    assert _q("SELECT trang_thai FROM kb_chunk WHERE title = 'test_kn bản nháp AI'")[0][0] == "cho_duyet"
    assert "test_kn mục sống" not in [h[2] for h in assistant.retrieve("test kn mục sống", k=19)]


def test_live_sample_and_drafts_loaded():
    counts = dict(_q("SELECT trang_thai, count(*) FROM kb_chunk WHERE title NOT LIKE 'test_kn%%' GROUP BY 1"))
    assert counts.get("dang_dung", 0) >= 11 and counts.get("cho_duyet", 0) >= 8
    assert _q("SELECT count(*) FROM kb_chunk WHERE cum_tu_khop = title AND title NOT LIKE 'test_kn%%'")[0][0] == 0


# ── 2.1 rules ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,flag", [
    ("Phí thiết kế 250.000 đ/m²", True), ("Biệt thự khoảng 1,5 tỷ", True), ("Gói từ 300 triệu", True), ("chỉ 45tr", True),
    ("Đơn giá 3.500.000 VND", True), ("Thiết kế mất 3 đến 4 tuần", False), ("Bảo hành 24 tháng", False),
    ("Quy trình 5 bước", False)])
def test_money_rule(text, flag):
    assert kn.needs_price_approval("faq", text) is flag
    assert kn.needs_price_approval("price", "không có số") is True


def test_price_entry_needs_an_approver():
    with _db() as c:
        e = _new(c, title="test_kn phí thiết kế", content="Phí thiết kế từ 250.000 đ/m².", trang_thai="cho_duyet")
        assert e["can_duyet_gia"] and e["trang_thai"] == "cho_duyet"
        with pytest.raises(kn.Forbidden):
            kn.set_status(c, CONTENT, e["id"], "dang_dung")
    with _db() as c:
        assert kn.set_status(c, LEAD, e["id"], "dang_dung")["trang_thai"] == "dang_dung"


def test_content_edit_of_live_price_goes_back_for_approval():
    with _db() as c:
        e = _new(c, LEAD, kind="price", title="test_kn giá gói", content="Gói cơ bản 300 triệu.")
        kn.set_status(c, LEAD, e["id"], "dang_dung")
        assert kn.update(c, CONTENT, e["id"], title="test_kn giá gói căn hộ")["trang_thai"] == "dang_dung"  # title only
        after = kn.update(c, CONTENT, e["id"], content="Gói cơ bản 350 triệu.")
        assert after["trang_thai"] == "cho_duyet"
        assert kn.update(c, LEAD, e["id"], content="Gói cơ bản 360 triệu.")["trang_thai"] == "cho_duyet"  # approver: unchanged
        general = _new(c, title="test_kn quy trình", content="Quy trình 5 bước.")
        kn.set_status(c, CONTENT, general["id"], "dang_dung")
        assert kn.update(c, CONTENT, general["id"], content="Quy trình 6 bước.")["trang_thai"] == "dang_dung"


def test_status_moves():
    with _db() as c:
        e = _new(c)
        with pytest.raises(kn.Invalid):
            kn.set_status(c, CONTENT, e["id"], "tat")            # a draft cannot be switched off
        for to in ("cho_duyet", "dang_dung", "tat", "dang_dung", "nhap"):
            assert kn.set_status(c, CONTENT, e["id"], to)["trang_thai"] == to
        with pytest.raises(kn.Invalid):
            kn.set_status(c, CONTENT, e["id"], "xoa")


def test_approving_an_ai_draft_strips_the_marker():
    with _db() as c:
        e = _new(c, kind="project", title="test_kn dự án AI", content=assistant.AI_MARK + " Căn hộ tông gỗ sáng.",
                 trang_thai="cho_duyet")
        assert e["ai"]
        on = kn.set_status(c, LEAD, e["id"], "dang_dung")
    assert on["content"] == "Căn hộ tông gỗ sáng." and not on["ai"] and on["nguon"] == "nhan_vien"


def test_edit_re_embeds():
    # topics no sample entry covers, so the ranking shows the new embedding rather than a near-duplicate
    first, second = "chỗ đỗ xe ô tô khi kiến trúc sư đến khảo sát", "có được nuôi mèo trong căn hộ mẫu không"
    with _db() as c:
        e = _new(c, title="test_kn câu hỏi thử", phrases=first, content="Nội dung thử.")
        kn.set_status(c, CONTENT, e["id"], "dang_dung")
    assert assistant.retrieve(first)[0][2] == "test_kn câu hỏi thử"
    before = _q("SELECT embedding::text FROM kb_chunk WHERE id=%s", e["id"])[0][0]
    with _db() as c:
        kn.update(c, CONTENT, e["id"], cum_tu_khop=second)
    assert _q("SELECT embedding::text FROM kb_chunk WHERE id=%s", e["id"])[0][0] != before
    assert assistant.retrieve(second)[0][2] == "test_kn câu hỏi thử"


def test_linked_service_title_is_protected():
    title = "Dịch vụ thiết kế phòng khách"
    row = _q("SELECT id, content FROM kb_chunk WHERE title = %s", title)
    if not row:
        pytest.skip("the sample service entries are not loaded")
    sid, text = row[0]
    try:
        with _db() as c:
            with pytest.raises(kn.Conflict):
                kn.update(c, LEAD, sid, title="Thiết kế phòng khách")
            with pytest.raises(kn.Conflict):
                kn.delete(c, LEAD, sid)
            assert kn.update(c, LEAD, sid, content=text + " (sửa thử)")["content"].endswith("(sửa thử)")
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE kb_chunk SET content = %s WHERE id = %s", (text, sid))
            c.execute("DELETE FROM nhat_ky_tri_thuc WHERE kb_chunk_id = %s AND created_at > now() - interval '1 minute'", (sid,))


def test_gaps_group_close_and_dismiss():
    with psycopg.connect(DSN) as c:
        a = c.execute("INSERT INTO khoang_trong_tri_thuc (cau_hoi, tu_chua_khop) VALUES "
                      "('test_kn Có làm văn phòng không?', '{van}'), ('test_kn co lam van phong khong', '{phong}') RETURNING id").fetchall()
        b = c.execute("INSERT INTO khoang_trong_tri_thuc (cau_hoi) VALUES ('test_kn nấu phở') RETURNING id").fetchone()[0]
    with _db() as c:
        groups = {g["cau_hoi"]: g for g in kn.gaps(c) if g["cau_hoi"].startswith("test_kn")}
    office = next(g for q, g in groups.items() if "văn phòng" in q or "van phong" in q)
    assert office["so_lan"] == 2 and set(office["tu_chua_khop"]) == {"van", "phong"}
    with _db() as c:
        e = _new(c, title="test_kn nội thất văn phòng", phrases="có làm nội thất văn phòng không",
                 content="Có, D3 Studio nhận thiết kế văn phòng.", tu_cau_hoi=office["ids"])
        kn.set_status(c, CONTENT, e["id"], "dang_dung")
        assert kn.dismiss_gaps(c, CONTENT, [b]) == 1
    assert {(s, k) for s, k in _q("SELECT trang_thai, kb_chunk_id FROM khoang_trong_tri_thuc WHERE id = ANY(%s)",
                                  [r[0] for r in a])} == {("da_xu_ly", e["id"])}
    assert _q("SELECT trang_thai FROM khoang_trong_tri_thuc WHERE id=%s", b)[0][0] == "bo_qua"
    with _db() as c:
        assert not [g for g in kn.gaps(c) if g["cau_hoi"].startswith("test_kn")]


def test_every_write_logs():
    with _db() as c:
        e = _new(c)
        kn.update(c, CONTENT, e["id"], content="Đổi trả trong 10 ngày.")
        kn.set_status(c, CONTENT, e["id"], "dang_dung")
        kn.delete(c, LEAD, e["id"])
    assert [r[0] for r in _q("SELECT hanh_dong FROM nhat_ky_tri_thuc WHERE kb_chunk_id=%s ORDER BY id", e["id"])] == \
        ["tao", "sua", "trang_thai", "xoa"]


# ── 2.2 API ────────────────────────────────────────────────────────────────────
def test_api_roles_and_errors(as_role):
    content, lead, sales = as_role("content"), as_role("lead_architect"), as_role("sales")
    assert client.get("/knowledge").status_code == 401
    assert client.get("/knowledge", headers=sales).status_code == 403
    body = {"kind": "faq", "title": "test_kn api", "cum_tu_khop": "test kn api", "content": "Nội dung API."}
    r = client.post("/knowledge", json=body, headers=content)
    assert r.status_code == 201 and r.json()["trang_thai"] == "nhap"
    eid = r.json()["id"]
    assert client.post("/knowledge", json=body, headers=content).status_code == 409
    listed = client.get("/knowledge", params={"q": "TEST KN API"}, headers=lead).json()
    item = next(i for i in listed["items"] if i["id"] == eid)
    assert {"can_duyet_gia", "mau", "lien_ket", "ai"} <= set(item) and listed["dem"]["nhap"] >= 1
    assert client.delete(f"/knowledge/{eid}", headers=content).status_code == 403
    price = client.post("/knowledge", json={**body, "title": "test_kn api giá", "content": "Từ 250.000 đ/m²"}, headers=content).json()
    r = client.post(f"/knowledge/{price['id']}/status", json={"trang_thai": "dang_dung"}, headers=content)
    assert r.status_code == 403 and "KTS trưởng" in r.json()["detail"]
    assert client.post(f"/knowledge/{price['id']}/status", json={"trang_thai": "dang_dung"}, headers=lead).status_code == 200
    linked = next((i for i in client.get("/knowledge", headers=lead).json()["items"] if i["lien_ket"]), None)
    if linked:
        assert client.patch(f"/knowledge/{linked['id']}", json={"title": "x đổi tên"}, headers=lead).status_code == 409
    assert client.delete(f"/knowledge/{eid}", headers=lead).status_code == 204
    assert client.get(f"/knowledge/{eid}", headers=lead).status_code == 404
    assert client.get("/knowledge/gaps", headers=content).status_code == 200


def test_chat_uses_only_live_entries(as_role):
    lead = as_role("lead_architect")
    body = {"kind": "faq", "title": "test_kn bảo dưỡng sàn gỗ",
            "cum_tu_khop": "bảo dưỡng sàn gỗ sau khi bàn giao như thế nào, lau sàn gỗ bằng gì",
            "content": "Lau sàn gỗ bằng khăn ẩm vắt kiệt, tránh nước đọng."}
    eid = client.post("/knowledge", json=body, headers=lead).json()["id"]
    question = {"message": "Bảo dưỡng sàn gỗ sau khi bàn giao thế nào?", "contact": "0922222222"}
    off = client.post("/chat", json=question).json()
    assert not off["sources"] or off["sources"][0]["title"] != body["title"]   # a draft is never said
    client.post(f"/knowledge/{eid}/status", json={"trang_thai": "dang_dung"}, headers=lead)
    on = client.post("/chat", json=question).json()
    assert on["answered"] and on["sources"][0]["title"] == body["title"] and on["answer"].startswith(body["content"])
    client.post(f"/knowledge/{eid}/status", json={"trang_thai": "tat"}, headers=lead)
    again = client.post("/chat", json=question).json()
    assert not again["sources"] or again["sources"][0]["title"] != body["title"]
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = %s", (question["message"],))
