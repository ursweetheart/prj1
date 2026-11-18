"""admin-tools 2.1: seq-14 b6-b9 on-demand object suggestions (fake detector)."""
import psycopg
import pytest
from psycopg.types.json import Jsonb

import api
from conftest import client
from pipeline.schemas import BoundingBox, DetectedFurniture, FurnitureDetectionResult
from pipeline.store import DSN


def _obj(label, vi, conf, x0, y0, x1, y1):
    return DetectedFurniture(label=label, label_vi=vi, confidence=conf, bbox=BoundingBox(x_min=x0, y_min=y0, x_max=x1, y_max=y1),
                             hotspot_anchor=((x0 + x1) / 2, (y0 + y1) / 2))


@pytest.fixture
def fake(monkeypatch):
    class Det:
        def detect(self, path):
            return FurnitureDetectionResult(objects=[_obj("couch", "Ghế sofa", 0.91, 0.1, 0.5, 0.5, 0.9),
                                                     _obj("potted plant", "Chậu cây", 0.6, 0.7, 0.2, 0.8, 0.5)],
                                            counts_by_category={}, inference_time_ms=1)
    monkeypatch.setattr(api, "_processor", lambda: type("P", (), {"detector": Det()})())


def test_suggestions_skip_what_is_already_marked(fake, drafts, as_role):
    [sid] = drafts(1)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET hotspots = %s WHERE id = %s",
                  (Jsonb({"objects": [{"label_vi": "Ghế sofa", "hotspot_anchor": [0.3, 0.7], "nguon_tao": "thu_cong"}]}), sid))
    r = client.post(f"/spaces/{sid}/detect", headers=as_role("architect"))
    assert r.status_code == 200
    got = r.json()
    assert [g["label_vi"] for g in got] == ["Chậu cây"]  # the sofa already has its hotspot inside the box
    assert got[0]["bbox"] == {"x_min": 0.7, "y_min": 0.2, "x_max": 0.8, "y_max": 0.5} and got[0]["confidence"] == 0.6


def test_accepted_suggestion_is_saved_as_ai_with_confidence(fake, drafts, as_role):
    [sid] = drafts(1)
    h = as_role("architect")
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET hotspots = %s WHERE id = %s", (Jsonb({"objects": []}), sid))
    g = client.post(f"/spaces/{sid}/detect", headers=h).json()[0]
    body = {"hotspots": [{"x": g["anchor"][0], "y": g["anchor"][1], "label_vi": g["label_vi"],
                          "goi_y_ai": {"label": g["label"], "confidence": g["confidence"], "bbox": g["bbox"]}}]}
    assert client.put(f"/spaces/{sid}/hotspots", json=body, headers=h).status_code == 200
    with psycopg.connect(DSN) as c:
        o = c.execute("SELECT hotspots->'objects'->0 FROM space WHERE id=%s", (sid,)).fetchone()[0]
    assert (o["nguon_tao"], o["confidence"], o["label_vi"]) == ("ai", 0.91, "Ghế sofa")


def test_roles_and_rate_limit(fake, drafts, as_role):
    [sid] = drafts(1)
    assert client.post(f"/spaces/{sid}/detect").status_code == 401
    assert client.post(f"/spaces/{sid}/detect", headers=as_role("visitor")).status_code == 403
    h = as_role("architect")
    codes = [client.post(f"/spaces/{sid}/detect", headers=h).status_code for _ in range(9)]
    assert codes[-1] == 429 and 200 in codes  # 10 per minute counting the two refused calls above
