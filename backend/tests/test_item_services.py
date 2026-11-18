"""Items linked to service packages (change topic-guard-sitemap-item-services; roadmap 1.9). Throw-away spaces
`test_is_*`, items `test-…` and service entries `TEST dịch vụ …`, all removed afterwards."""
import uuid

import psycopg
import pytest
from psycopg.types.json import Jsonb

from conftest import client
from pipeline import items
from pipeline.store import DSN

LIVING, BEDROOM = "Dịch vụ thiết kế phòng khách", "Dịch vụ thiết kế phòng ngủ"
SUPPLIER = "NhaCungCapBiMat-" + uuid.uuid4().hex[:6]


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def world():
    made = {"spaces": [], "items": [], "kb": []}

    def kb(kind="service", status="dang_dung"):
        with psycopg.connect(DSN) as c:
            kid = c.execute("INSERT INTO kb_chunk (kind, title, content, trang_thai) VALUES (%s, %s, 'x', %s) RETURNING id",
                            (kind, f"TEST dịch vụ {uuid.uuid4().hex[:6]}", status)).fetchone()[0]
        made["kb"].append(kid)
        return kid

    def item(**kw):
        with psycopg.connect(DSN) as c:
            it = items.create(c, {"ten": "test-" + uuid.uuid4().hex[:8], **kw})
        made["items"].append(it["id"])
        return it

    def space(objects):
        with psycopg.connect(DSN) as c:
            sid = c.execute("INSERT INTO space (relative_path, space_type, review_status, hotspots) VALUES (%s, 'phong_khach', "
                            "'published', %s) RETURNING id", (f"test_is_{uuid.uuid4().hex[:8]}/x.jpg",
                                                               Jsonb({"objects": objects}))).fetchone()[0]
        made["spaces"].append(sid)
        return sid

    yield type("W", (), {"kb": staticmethod(kb), "item": staticmethod(item), "space": staticmethod(space)})
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made["spaces"],))
        c.execute("DELETE FROM mon_do WHERE id = ANY(%s)", (made["items"],))
        c.execute("DELETE FROM kb_chunk WHERE id = ANY(%s)", (made["kb"],))


def _living():
    return _q("SELECT id FROM kb_chunk WHERE title = %s AND kind = 'service'", LIVING)[0][0]


def _cards(sid):
    r = client.get(f"/spaces/{sid}")
    assert r.status_code == 200
    assert SUPPLIER not in r.text
    return [o.get("service") for o in r.json()["hotspots"]["objects"]]


def test_link_validation_and_delete_clears(world, as_role):
    h = as_role("architect")
    it = world.item()
    faq = world.kb(kind="faq")
    bad = client.patch(f"/items/{it['id']}", json={"dich_vu_id": faq}, headers=h)
    assert bad.status_code == 422 and bad.json()["detail"][0]["loc"] == ["body", "dich_vu_id"]
    assert _q("SELECT dich_vu_id FROM mon_do WHERE id = %s", it["id"]) == [(None,)]
    svc = world.kb()
    ok = client.patch(f"/items/{it['id']}", json={"dich_vu_id": svc}, headers=h).json()
    assert ok["dich_vu_id"] == svc and ok["dich_vu"].startswith("TEST dịch vụ")
    listed = next(i for i in client.get("/items", params={"q": it["ten"]}, headers=h).json() if i["id"] == it["id"])
    assert listed["dich_vu_id"] == svc
    services = client.get("/items/services", headers=h).json()
    assert any(s["id"] == svc for s in services) and all(s["id"] != faq for s in services)
    assert client.get("/items/services", headers=as_role("visitor")).status_code == 403
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM kb_chunk WHERE id = %s", (svc,))
    assert _q("SELECT dich_vu_id FROM mon_do WHERE id = %s", it["id"]) == [(None,)]


def test_cards_show_item_service_first(world):
    it = world.item(dich_vu_id=_living(), nha_cung_cap=SUPPLIER)
    plain = world.item()
    sid = world.space([
        {"nguon_tao": "thu_cong", "hotspot_anchor": [0.1, 0.2], "label_vi": "Đèn thả", "mon_do_id": it["id"]},
        {"label": "bed", "label_vi": "Giường", "hotspot_anchor": [0.5, 0.5], "mon_do_id": it["id"]},
        {"label": "bed", "label_vi": "Giường", "hotspot_anchor": [0.6, 0.5], "mon_do_id": plain["id"]},
        {"nguon_tao": "thu_cong", "hotspot_anchor": [0.3, 0.3], "label_vi": "Thảm", "mon_do_id": plain["id"]}])
    assert _cards(sid) == [LIVING, LIVING, BEDROOM, None]


def test_service_not_in_use_is_hidden(world):
    off = world.kb(status="tat")
    it = world.item(dich_vu_id=off)
    sid = world.space([
        {"nguon_tao": "thu_cong", "hotspot_anchor": [0.1, 0.2], "label_vi": "Đèn thả", "mon_do_id": it["id"]},
        {"label": "bed", "label_vi": "Giường", "hotspot_anchor": [0.5, 0.5], "mon_do_id": it["id"]}])
    assert _cards(sid) == [None, BEDROOM]
