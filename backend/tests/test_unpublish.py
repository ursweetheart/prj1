"""Taking published photos down (change unpublish-photos). Throw-away spaces 'test_up_*', a test item, a saved
collection and a sent copy, all removed afterwards."""
import logging
import uuid

import psycopg
import pytest
from psycopg.types.json import Jsonb

from conftest import client
from pipeline import items, notify, project_stats
from pipeline.store import DSN

REASON = "Khách rút lại đồng ý công bố"


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def photos():
    made = []

    def make(status="published", n=1, uploader_id=None, folder=None):
        ids = []
        with psycopg.connect(DSN) as c:
            for _ in range(n):
                f = folder or f"test_up_{uuid.uuid4().hex[:6]}"
                sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status) VALUES "
                                "(%s, 'phong_khach', 'Japandi', %s) RETURNING id", (f"{f}/{uuid.uuid4().hex[:4]}.jpg", status)).fetchone()[0]
                if uploader_id:
                    c.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, %s, 'ingest', '{}')",
                              (sid, uploader_id))
                ids.append(sid)
        made.extend(ids)
        return ids

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made,))


def _st(sid):
    return _q("SELECT review_status, ly_do_duyet FROM space WHERE id = %s", sid)[0]


def _down(ids, headers, internal=False, reason=REASON):
    return client.post("/spaces/unpublish", json={"space_ids": ids, "ly_do": reason, "giu_noi_bo": internal}, headers=headers)


# ── 1.1 endpoint ────────────────────────────────────────────────────────────────
def test_take_down_to_draft_and_to_internal(photos, as_role):
    lead = as_role("lead_architect")
    a, b = photos(n=2)
    r = _down([a], lead)
    assert r.status_code == 200 and r.json() == {"moved": [a], "status": "draft"}
    st, shown = _st(a)
    assert st == "draft" and shown["loai"] == "go_xuong" and shown["ly_do"] == REASON
    log = _q("SELECT action, detail FROM review_log WHERE space_id = %s ORDER BY id DESC LIMIT 1", a)[0]
    assert log[0] == "unpublish" and log[1]["from"] == "published" and log[1]["to"] == "draft"
    assert _down([b], lead, internal=True).json()["status"] == "noi_bo"
    assert _st(b)[1]["loai"] == "go_noi_bo"
    returned = {s["id"] for s in client.get("/spaces", params={"review_status": "draft", "tra_ve": 1, "limit": 200},
                                            headers=lead).json()}
    assert a in returned
    assert client.post("/spaces/reopen", json={"space_ids": [b], "ly_do": "Khách đã đồng ý lại"}, headers=lead).json()["status"] == "draft"


def test_mixed_selection_and_rules(photos, as_role):
    lead = as_role("admin")
    pub, draft = photos(), photos("draft")
    r = _down(pub + draft, lead)
    assert r.status_code == 409 and str(draft[0]) in r.text
    assert _st(pub[0])[0] == "published" and _st(draft[0])[0] == "draft"
    assert _down(pub, lead, reason="sai").status_code == 422
    for role in ("architect", "content"):
        assert _down(pub, as_role(role)).status_code == 403
    assert _down(pub, {}).status_code == 401
    assert client.post("/spaces/return", json={"space_ids": pub, "ly_do": REASON}, headers=lead).status_code == 409
    assert _st(pub[0])[0] == "published"


def test_uploader_told(photos, as_role, monkeypatch, caplog):
    monkeypatch.delenv("D3_SMTP_HOST", raising=False)
    arch = as_role("architect")
    me = client.get("/auth/me", headers=arch).json()["id"]
    sid, = photos(uploader_id=me)
    with caplog.at_level(logging.INFO, logger="d3.review"):
        notify.notify_returned([(sid, "x.jpg", "go_xuong", REASON)], "lead@example.com")
    assert "Gỡ khỏi website" in caplog.text and REASON in caplog.text


# ── 1.2 public trace ────────────────────────────────────────────────────────────
def test_taken_down_photo_leaves_every_public_place(photos, as_role):
    lead, visitor = as_role("lead_architect"), as_role("visitor")
    src = _q("SELECT id, relative_path, caption FROM space WHERE review_status = 'published' AND embedding IS NOT NULL "
             "AND space_type = 'phong_khach' ORDER BY id LIMIT 1")
    if not src:
        pytest.skip("no published living-room photo with an embedding")
    src_id, src_path, caption = src[0]
    folder = f"test_up_{uuid.uuid4().hex[:6]}"
    sid, = photos(folder=folder)
    with psycopg.connect(DSN) as c:  # a twin of a real photo, so similarity search must find it
        c.execute("UPDATE space SET embedding = (SELECT embedding FROM space WHERE id = %s), caption = %s, "
                  "hotspots = %s WHERE id = %s", (src_id, caption, Jsonb({"objects": []}), sid))
        c.execute("INSERT INTO review_log (space_id, action, detail) VALUES (%s, 'advance', %s)",
                  (sid, Jsonb({"from": "cleared", "to": "published"})))
        it = items.create(c, {"ten": f"test-up-{uuid.uuid4().hex[:6]}"})
        c.execute("UPDATE space SET hotspots = %s WHERE id = %s",
                  (Jsonb({"objects": [{"nguon_tao": "thu_cong", "label_vi": "Sofa", "hotspot_anchor": [0.5, 0.5],
                                       "mon_do_id": it["id"]}]}), sid))
        code = "TUP" + uuid.uuid4().hex[:9].upper()
        brief = c.execute("INSERT INTO bo_suu_tap (loai, ma_chia_se) VALUES ('da_gui', %s) RETURNING id", (code,)).fetchone()[0]
        c.execute("INSERT INTO bo_suu_tap_anh (bo_suu_tap_id, space_id) VALUES (%s, %s)", (brief, sid))
    assert client.put(f"/collections/me/items/{sid}", json={}, headers=visitor).status_code in (200, 204)

    def places():
        ids = lambda rows: {r["id"] for r in rows}  # noqa: E731
        with psycopg.connect(DSN) as c:
            stats = {p["folder"] for p in project_stats.overview(c, 30)["projects"]}
        saved = client.get("/collections/me", headers=visitor).json()
        saved_ids = {x.get("space_id", x.get("id")) for x in (saved.get("items", saved) if isinstance(saved, dict) else saved)}
        shared = client.get(f"/collections/shared/{code}").json()
        shared_ids = {x.get("space_id", x.get("id")) for x in shared.get("items", shared.get("anh", []))}
        return {
            "space_page": client.get(f"/spaces/{sid}").status_code == 200,
            "list": sid in ids(client.get("/spaces", params={"limit": 200}).json()),
            "similar": sid in ids(client.get(f"/spaces/{src_id}/similar", params={"k": 24}).json()),
            "project": sid in ids(client.get(f"/projects/{folder}/spaces").json()),
            "item": sid in ids(client.get(f"/items/{it['id']}/spaces").json()["spaces"]),
            "stats": folder in stats,
            "saved": sid in saved_ids,
            "sent": sid in shared_ids,
        }

    try:
        before = places()
        assert all(before.values()), before
        assert _down([sid], lead).status_code == 200
        after = places()
        assert not any(after.values()), after
        assert client.get(f"/spaces/{sid}").status_code == 404
        text = client.get("/search", params={"q": caption or "phòng khách", "k": 24}).json()["ket_qua"]
        assert sid not in {r["id"] for r in text}
        with psycopg.connect(DSN) as c:  # published again: it is back where it was saved or sent
            c.execute("UPDATE space SET review_status = 'published' WHERE id = %s", (sid,))
        again = places()
        assert again["saved"] and again["sent"], again
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM bo_suu_tap WHERE ma_chia_se = %s", (code,))
            c.execute("DELETE FROM bo_suu_tap_anh WHERE space_id = %s", (sid,))
            c.execute("DELETE FROM space WHERE id = %s", (sid,))
            c.execute("DELETE FROM mon_do WHERE id = %s", (it["id"],))
