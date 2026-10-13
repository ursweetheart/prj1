"""RAG assistant skeleton. Needs Postgres with kb/sample.json loaded (python -m pipeline.assistant kb/sample.json)."""
import psycopg

from conftest import client
from pipeline.assistant import parse_request
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


def test_answer_has_sources_and_creates_price_lead():
    before = _leads()
    try:
        r = client.post("/chat", json={"message": "Làm nội thất biệt thự tính phí thế nào?", "contact": "0900000000"}).json()
        assert r["answered"] and r["sources"][0]["title"] == "Bảng giá thiết kế nội thất biệt thự"
        assert r["lead_id"] and _leads() == before + 1
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE id > 0 AND contact = '0900000000'")


def test_off_topic_is_refused_and_handed_off():
    try:
        r = client.post("/chat", json={"message": "Cách nấu phở bò ngon", "contact": "0911111111"}).json()
        assert not r["answered"] and not r["sources"] and not r["images"] and "chưa có thông tin" in r["answer"]
        with psycopg.connect(DSN) as c:
            assert c.execute("SELECT intent FROM lead WHERE id=%s", (r["lead_id"],)).fetchone()[0] == "handoff"
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE contact = '0911111111'")


def test_chat_images_only_published(as_role):
    admin = as_role("admin")
    q = {"message": "Bên bạn thiết kế phòng khách gồm những gì?"}
    assert client.post("/chat", json=q).json()["images"] == []  # nothing published yet
    ids = [x["id"] for x in client.get("/spaces", params={"space_type": "phong_khach", "limit": 3}, headers=admin).json()]
    try:
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE space SET review_status='published' WHERE id = ANY(%s)", (ids,))
        imgs = client.post("/chat", json=q).json()["images"]
        assert imgs and {i["id"] for i in imgs} <= set(ids)
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE conversation @> '[{\"content\": \"%s\"}]'::jsonb" % q["message"])
            c.execute("UPDATE space SET review_status='draft' WHERE id = ANY(%s)", (ids,))


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
