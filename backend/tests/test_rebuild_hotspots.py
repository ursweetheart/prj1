"""Re-run for untouched drafts (change: hotspot-accuracy 3.1). The classifier is never called: items are given by hand.
Throw-away spaces 'test_rbh_*' are removed afterwards with their log rows."""

import json
import uuid

import psycopg
import pytest
from psycopg.types.json import Jsonb

import rebuild_hotspots as rb
from pipeline.schemas import AiItem
from pipeline.store import DSN


def obj(label, conf, x0, y0, x1, y1, **extra):
    return {"label": label, "label_vi": label, "confidence": conf, "hotspot_anchor": [(x0 + x1) / 2, (y0 + y1) / 2],
            "bbox": {"x_min": x0, "y_min": y0, "x_max": x1, "y_max": y1}, **extra}


NOISY = [obj("couch", 0.9, 0.1, 0.5, 0.7, 0.9), obj("couch", 0.6, 0.12, 0.52, 0.68, 0.88), obj("bottle", 0.9, 0.5, 0.5, 0.52, 0.55),
         obj("cup", 0.8, 0.6, 0.6, 0.62, 0.62), obj("chair", 0.3, 0.8, 0.6, 0.9, 0.8)]
ITEMS = [AiItem(ten="Sofa chữ L", loai="sofa", x=0.2, y=0.75), AiItem(ten="Đèn chùm", loai="den", x=0.5, y=0.1)]


@pytest.fixture
def spaces():
    made = []

    def make(objects, status="draft", log_action=None):
        with psycopg.connect(DSN) as c:
            sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status, palette, hotspots) "
                            "VALUES (%s, 'phong_khach', 'Hien_dai', %s, %s, %s) RETURNING id",
                            (f"test_rbh_p/{uuid.uuid4().hex[:8]}.jpg", status, Jsonb({}),
                             Jsonb({"objects": objects, "counts_by_category": {}, "inference_time_ms": 1}))).fetchone()[0]
            if log_action:
                c.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, NULL, %s, '{}')", (sid, log_action))
        made.append(sid)
        return sid

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM review_log WHERE space_id = ANY(%s)", (made,))
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made,))


def _objects(sid):
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT hotspots->'objects' FROM space WHERE id = %s", (sid,)).fetchone()[0]


def _selected(conn, ids):
    return {r[0] for r in rb.untouched(conn)} & set(ids)


def test_only_untouched_drafts_are_selected(spaces):
    clean = spaces(NOISY)
    hand = spaces(NOISY + [{"label_vi": "Điểm tay", "hotspot_anchor": [0.5, 0.5], "nguon_tao": "thu_cong"}])
    linked = spaces([obj("couch", 0.9, 0.1, 0.5, 0.7, 0.9, mon_do_id=1)])
    dragged = spaces(NOISY, log_action="hotspots")
    published = spaces(NOISY, status="published")
    with psycopg.connect(DSN) as c:
        assert _selected(c, [clean, hand, linked, dragged, published]) == {clean}


def test_rebuild_cleans_caps_logs_and_is_not_repeated(spaces):
    sid = spaces(NOISY)
    with psycopg.connect(DSN) as c:
        row = next(r for r in rb.untouched(c) if r[0] == sid)
        assert rb.write(c, row, ITEMS) == 2
        assert _selected(c, [sid]) == set()  # rebuilt once: not picked again
    objs = _objects(sid)
    assert [(o["label_vi"], o["nguon_ai"]) for o in objs] == [("Sofa chữ L", "ca_hai"), ("Đèn chùm", "gemini")]
    with psycopg.connect(DSN) as c:
        log = c.execute("SELECT detail FROM review_log WHERE space_id = %s AND action = 'rebuild_hotspots'", (sid,)).fetchone()[0]
    assert log["so_truoc"] == 5 and log["so_sau"] == 2 and log["truoc"] == json.loads(json.dumps(NOISY))


def test_restore_puts_back_unless_edited_since(spaces):
    a, b = spaces(NOISY), spaces(NOISY)
    with psycopg.connect(DSN) as c:
        for r in [r for r in rb.untouched(c) if r[0] in (a, b)]:
            rb.write(c, r, ITEMS)
        c.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, NULL, 'hotspots', '{}')", (b,))
        assert rb.restore(c, [a, b]) == 1  # only these test photos, never the real library
    assert len(_objects(a)) == 5          # restored
    assert len(_objects(b)) == 2          # a person edited it after the rebuild: theirs stays
    with psycopg.connect(DSN) as c:
        assert rb.restore(c, [a, b]) == 0  # a second restore changes nothing
        assert _selected(c, [a, b]) == {a}  # restored: may be rebuilt again; b was edited by hand


def test_heuristic_answer_is_a_failure_not_an_empty_list():
    class Clf:
        def classify(self, *a):
            return type("R", (), {"llm_usage": None, "items": []})()
    with pytest.raises(RuntimeError):
        rb.items_for(Clf(), (1, "x/y.jpg", {"palette": [], "dominant_hex": "#fff", "brightness": "light",
                                            "temperature": "warm", "weighted_luminance": 50},
                             {"objects": [], "counts_by_category": {}, "inference_time_ms": 1}))
