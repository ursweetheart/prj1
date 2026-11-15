"""Hotspots by hand and the item library (change hotspot-items). Throw-away spaces `test_hi_*/x.jpg` and items named
`test-…`, all removed afterwards."""
import uuid

import psycopg
import pytest
from psycopg.types.json import Jsonb

from conftest import client
from pipeline import items
from pipeline.store import DSN

SUPPLIER = "NhaCungCapBiMat-" + uuid.uuid4().hex[:6]
DETECTED = {"objects": [
    {"label": "couch", "label_vi": "Sofa", "confidence": 0.8, "bbox": {"x_min": .2, "y_min": .5, "x_max": .6, "y_max": .9},
     "hotspot_anchor": [0.4, 0.7]},
    {"label": "chair", "label_vi": "Ghế", "confidence": 0.5, "bbox": {"x_min": .7, "y_min": .5, "x_max": .8, "y_max": .7},
     "hotspot_anchor": [0.75, 0.6]}],
    "counts_by_category": {"couch": 1, "chair": 1}, "inference_time_ms": 10.0}


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def world():
    made = {"spaces": [], "items": []}

    def space(status="published", hotspots=DETECTED):
        with psycopg.connect(DSN) as c:
            sid = c.execute("INSERT INTO space (relative_path, space_type, review_status, hotspots) VALUES (%s, 'phong_khach', "
                            "%s, %s) RETURNING id", (f"test_hi_{uuid.uuid4().hex[:8]}/x.jpg", status, Jsonb(hotspots))).fetchone()[0]
        made["spaces"].append(sid)
        return sid

    def item(name=None, **kw):
        with psycopg.connect(DSN) as c:
            it = items.create(c, {"ten": name or "test-" + uuid.uuid4().hex[:8], **kw})
        made["items"].append(it["id"])
        return it

    def link(sid, item_id):
        with psycopg.connect(DSN) as c:
            cur = c.execute("SELECT hotspots FROM space WHERE id=%s", (sid,)).fetchone()[0]
            cur["objects"][0]["mon_do_id"] = item_id
            c.execute("UPDATE space SET hotspots=%s WHERE id=%s", (Jsonb(cur), sid))

    yield type("W", (), {"space": staticmethod(space), "item": staticmethod(item), "link": staticmethod(link), "made": made})
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made["spaces"],))
        c.execute("DELETE FROM mon_do WHERE id = ANY(%s) OR ten LIKE 'test-%%'", (made["items"],))


# ── 1.2 module ──────────────────────────────────────────────────────────────────
def test_key_ignores_case_accents_spaces():
    assert items.key("Sofa vải lanh  xám") == items.key("sofa vai lanh xam") == "sofa vai lanh xam"
    assert items.key("Đèn thả") == "den tha"


def test_duplicate_names(world):
    a = world.item("test-Sofa vải lanh xám")
    with psycopg.connect(DSN) as c:
        with pytest.raises(items.Conflict) as e:
            items.create(c, {"ten": "TEST-sofa vai lanh xam"})
        assert e.value.existing["id"] == a["id"]
        b = world.item("test-Bàn ăn gỗ")
        with pytest.raises(items.Conflict):
            items.update(c, b["id"], {"ten": "test sofa vải lanh xám"})


def test_delete_in_use(world):
    used, free = world.item(), world.item()
    for _ in range(3):
        world.link(world.space(), used["id"])
    with psycopg.connect(DSN) as c:
        with pytest.raises(items.InUse) as e:
            items.delete(c, used["id"])
        assert e.value.n == 3
        items.delete(c, free["id"])
    assert _q("SELECT count(*) FROM mon_do WHERE id = %s", free["id"])[0][0] == 0


def test_validate_moves_adds_and_counts(world):
    it = world.item()
    with psycopg.connect(DSN) as c:
        doc = items.validate_hotspots(c, DETECTED, [
            {"index": 0, "x": 0.45, "y": 0.72, "label_vi": "Sofa vải", "mon_do_id": it["id"]},
            {"x": 0.1, "y": 0.2, "label_vi": "Đèn thả"}])
    moved, new = doc["objects"]
    assert moved["label"] == "couch" and moved["bbox"] == DETECTED["objects"][0]["bbox"] and moved["confidence"] == 0.8
    assert moved["nguon_tao"] == "ai" and moved["hotspot_anchor"] == [0.45, 0.72] and moved["mon_do_id"] == it["id"]
    assert new == {"nguon_tao": "thu_cong", "hotspot_anchor": [0.1, 0.2], "label_vi": "Đèn thả", "mon_do_id": None}
    assert doc["counts_by_category"] == {"couch": 1} and doc["inference_time_ms"] == 10.0


@pytest.mark.parametrize("bad, row", [
    ([{"x": 1.2, "y": 0.5, "label_vi": "A"}], 0),
    ([{"x": 0.5, "y": 0.5, "label_vi": "A"}, {"x": 0.5, "y": 0.5, "label_vi": "  "}], 1),
    ([{"x": 0.5, "y": 0.5, "label_vi": "A", "mon_do_id": 999999999}], 0),
    ([{"index": 9, "x": 0.5, "y": 0.5, "label_vi": "A"}], 0),
    ([{"x": 0.5, "y": 0.5, "label_vi": "A"}] * 31, None),
])
def test_validate_rejects(bad, row):
    with psycopg.connect(DSN) as c:
        with pytest.raises(items.Invalid) as e:
            items.validate_hotspots(c, DETECTED, bad)
    assert e.value.row == row


def test_spaces_for_published_only_unless_staff(world):
    it = world.item(nha_cung_cap=SUPPLIER)
    pub, draft = world.space(), world.space("draft")
    world.link(pub, it["id"]); world.link(draft, it["id"])
    with psycopg.connect(DSN) as c:
        public = items.spaces_for(c, it["id"], staff=False)
        staff = items.spaces_for(c, it["id"], staff=True)
    assert [s["id"] for s in public["spaces"]] == [pub] and set(public["mon_do"]) == {"id", "ten", "phan_loai"}
    assert {s["id"] for s in staff["spaces"]} == {pub, draft} and staff["mon_do"]["nha_cung_cap"] == SUPPLIER


# ── 1.3 endpoints ───────────────────────────────────────────────────────────────
def test_write_roles(world, as_role):
    sid, it = world.space(), world.item()
    body = {"hotspots": [{"x": 0.5, "y": 0.5, "label_vi": "A"}]}
    for role in ("content", "visitor"):
        h = as_role(role)
        assert client.put(f"/spaces/{sid}/hotspots", json=body, headers=h).status_code == 403
        assert client.get("/items", headers=h).status_code == 403
        assert client.post("/items", json={"ten": "test-x"}, headers=h).status_code == 403
        assert client.patch(f"/items/{it['id']}", json={"ten": "test-y"}, headers=h).status_code == 403
        assert client.delete(f"/items/{it['id']}", headers=h).status_code == 403
    assert client.put(f"/spaces/{sid}/hotspots", json=body).status_code == 401
    assert client.get("/items").status_code == 401


def test_save_shows_on_space_and_logs(world, as_role):
    sid, it = world.space(), world.item(nha_cung_cap=SUPPLIER)
    h = as_role("architect")
    r = client.put(f"/spaces/{sid}/hotspots", headers=h, json={"hotspots": [
        {"index": 0, "x": 0.45, "y": 0.72, "label_vi": "Sofa vải", "mon_do_id": it["id"]},
        {"x": 0.1, "y": 0.2, "label_vi": "Đèn thả"}]})
    assert r.status_code == 200, r.text
    objs = client.get(f"/spaces/{sid}").json()["hotspots"]["objects"]
    assert [(o["label_vi"], o["nguon_tao"]) for o in objs] == [("Sofa vải", "ai"), ("Đèn thả", "thu_cong")]
    assert objs[0]["service"] and objs[1]["service"] is None  # the sofa keeps its service; a hand point has none
    log = _q("SELECT detail FROM review_log WHERE space_id = %s AND action = 'hotspots'", sid)
    assert log and log[-1][0] == {"truoc": 2, "sau": 2, "thu_cong": 1, "lien_ket": 1}
    before = _q("SELECT hotspots FROM space WHERE id = %s", sid)[0][0]
    bad = client.put(f"/spaces/{sid}/hotspots", headers=h, json={"hotspots": [{"x": 1.2, "y": 0.2, "label_vi": "X"}]})
    assert bad.status_code == 422 and bad.json()["detail"][0]["loc"] == ["body", "hotspots", 0]
    assert _q("SELECT hotspots FROM space WHERE id = %s", sid)[0][0] == before
    assert client.put("/spaces/999999999/hotspots", headers=h, json={"hotspots": []}).status_code == 404


def test_item_endpoints(world, as_role):
    h = as_role("lead_architect")
    r = client.post("/items", headers=h, json={"ten": "test-Đèn thả mây", "phan_loai": "Đèn thả", "vat_lieu": "Mây tre"})
    assert r.status_code == 201
    it = r.json()
    world.made["items"].append(it["id"])
    dup = client.post("/items", headers=h, json={"ten": "TEST-den tha may"})
    assert dup.status_code == 409 and dup.json()["detail"]["existing"]["ten"] == "test-Đèn thả mây"
    assert client.patch(f"/items/{it['id']}", headers=h, json={"mau_sac": "Nâu"}).json()["mau_sac"] == "Nâu"
    found = client.get("/items", params={"q": "may tre"}, headers=h).json()
    assert any(x["id"] == it["id"] and x["so_anh"] == 0 for x in found)
    world.link(world.space(), it["id"])
    gone = client.delete(f"/items/{it['id']}", headers=h)
    assert gone.status_code == 409 and gone.json()["detail"]["so_anh"] == 1
    assert client.delete("/items/999999999", headers=h).status_code == 404
    assert client.post("/items", headers=h, json={"ten": "  "}).status_code == 422


def test_no_supplier_in_public_outputs(world):
    it = world.item(nha_cung_cap=SUPPLIER, ghi_chu="ghi chú nội bộ")
    pub, draft = world.space(), world.space("draft")
    world.link(pub, it["id"]); world.link(draft, it["id"])
    r = client.get(f"/items/{it['id']}/spaces").json()
    assert [s["id"] for s in r["spaces"]] == [pub] and "nha_cung_cap" not in r["mon_do"] and "ghi_chu" not in r["mon_do"]
    for path in (f"/items/{it['id']}/spaces", f"/spaces/{pub}", "/spaces?limit=200"):
        assert SUPPLIER not in client.get(path).text
    assert client.get("/items/999999999/spaces").status_code == 404


def test_relabel_skips_hand_points(monkeypatch):
    import relabel
    seen = {}

    class Fake:
        def classify(self, path, palette, furniture):
            seen["labels"] = [o.label for o in furniture.objects]
            return type("R", (), {"llm_usage": {}})()
    from pipeline.color_extractor import ColorAnalysisResult
    pal = ColorAnalysisResult.model_construct()
    monkeypatch.setattr(relabel.ColorAnalysisResult, "model_validate", staticmethod(lambda p: pal))
    hotspots = {**DETECTED, "objects": DETECTED["objects"] + [{"nguon_tao": "thu_cong", "label_vi": "Đèn thả",
                                                               "hotspot_anchor": [0.1, 0.2], "mon_do_id": None}]}
    relabel.classify(Fake(), (1, "x.jpg", {}, hotspots))
    assert seen["labels"] == ["couch", "chair"]
