"""QT-01 on the review API (change: cms-publishing-workflow). Needs Postgres up + ingested data.
Every test puts the spaces it touches back as it found them."""
import psycopg
import pytest
from psycopg.types.json import Jsonb

from conftest import client
from pipeline.store import DSN

COLS = "review_status, space_type, design_style, caption, alt_text, materials, hotspots"


@pytest.fixture
def drafts():
    """drafts(n) -> ids of n draft spaces, restored (columns, human tags, log) after the test."""
    taken = []

    def take(n, where="TRUE"):
        with psycopg.connect(DSN) as c:
            rows = c.execute(f"SELECT id, {COLS} FROM space WHERE review_status='draft' AND {where} ORDER BY id LIMIT %s",
                             (n,)).fetchall()
        taken.extend(rows)
        return [r[0] for r in rows]

    yield take
    with psycopg.connect(DSN) as c:
        for sid, *vals in taken:
            vals[-1] = Jsonb(vals[-1])  # hotspots
            c.execute(f"UPDATE space SET ({COLS}) = (%s,%s,%s,%s,%s,%s,%s) WHERE id=%s", (*vals, sid))
            c.execute("DELETE FROM space_gia_tri WHERE space_id=%s AND nguon_tao='nguoi'", (sid,))
            c.execute("DELETE FROM review_log WHERE space_id=%s", (sid,))


def _space(sid, h):
    return client.get(f"/spaces/{sid}", headers=h).json()


def _tags(sid, h):
    rows = client.get("/spaces", params={"review_status": _space(sid, h)["review_status"], "limit": 200}, headers=h).json()
    return next(r for r in rows if r["id"] == sid)["tags"]


# ── 2. AI content + content role ─────────────────────────────────────────────

def test_edit_text_and_materials_retags_and_logs(as_role, drafts):
    h = as_role("architect")
    [sid] = drafts(1)
    r = client.patch(f"/spaces/{sid}", headers=h, json={"caption": "Phòng khách gỗ óc chó", "materials": [" gỗ óc chó ", ""]})
    assert r.status_code == 200 and r.json()["caption"] == "Phòng khách gỗ óc chó" and r.json()["materials"] == ["gỗ óc chó"]
    assert _tags(sid, h)["vat_lieu"] == ["go"]
    with psycopg.connect(DSN) as c:
        action, detail = c.execute("SELECT action, detail FROM review_log WHERE space_id=%s ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
    assert action == "edit" and detail["to"]["materials"] == ["gỗ óc chó"] and "caption" in detail["from"]


def test_content_role_edits_text_only_in_review(as_role, drafts):
    lead, content = as_role("lead_architect"), as_role("content")
    [sid] = drafts(1)
    assert client.patch(f"/spaces/{sid}", headers=content, json={"caption": "x"}).status_code == 403  # still a draft
    client.patch(f"/spaces/{sid}", headers=lead, json={"advance": True})
    assert client.patch(f"/spaces/{sid}", headers=content, json={"caption": "Biên tập"}).json()["caption"] == "Biên tập"
    assert client.patch(f"/spaces/{sid}", headers=content, json={"design_style": "Japandi"}).status_code == 403
    assert client.patch(f"/spaces/{sid}", headers=content, json={"advance": True}).status_code == 403
    assert _space(sid, lead)["review_status"] == "in_review"


# ── 3. cleared + bulk advance ────────────────────────────────────────────────

def test_full_order_through_cleared(as_role, drafts):
    lead, arch = as_role("lead_architect"), as_role("architect")
    [sid] = drafts(1)
    for want in ("in_review", "approved"):
        assert client.patch(f"/spaces/{sid}", headers=lead, json={"advance": True}).json()["review_status"] == want
    assert client.patch(f"/spaces/{sid}", headers=arch, json={"advance": True, "rights_confirmed": True}).status_code == 403
    assert client.patch(f"/spaces/{sid}", headers=lead, json={"advance": True}).status_code == 422  # no rights confirmation
    assert _space(sid, lead)["review_status"] == "approved"
    assert client.patch(f"/spaces/{sid}", headers=lead, json={"advance": True, "rights_confirmed": True}).json()["review_status"] == "cleared"
    assert client.patch(f"/spaces/{sid}", headers=lead, json={"advance": True}).json()["review_status"] == "published"
    assert client.patch(f"/spaces/{sid}", headers=lead, json={"advance": True}).status_code == 409


def test_bulk_advance_all_or_nothing(as_role, drafts):
    lead = as_role("lead_architect")
    a, b, c = drafts(3)
    r = client.post("/spaces/advance", headers=lead, json={"space_ids": [a, b, c]})
    assert r.status_code == 200 and r.json() == {"advanced": sorted([a, b, c]), "status": ["in_review"]}
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE space SET review_status='published' WHERE id=%s", (c,))
    r = client.post("/spaces/advance", headers=lead, json={"space_ids": [a, b, c]})
    assert r.status_code == 409 and str(c) in r.json()["detail"]
    assert [_space(x, lead)["review_status"] for x in (a, b)] == ["in_review", "in_review"]  # rolled back


# ── 4. human tags ────────────────────────────────────────────────────────────

def test_tag_a_project_then_replace(as_role, drafts):
    h = as_role("architect")
    ids = drafts(200, "split_part(relative_path, '/', 1) = 'working_space'")
    assert ids, "needs the working_space project ingested"
    r = client.put("/spaces/tags", headers=h, json={"project": "working_space", "dimension": "loai_cong_trinh", "values": ["biet_thu"]})
    assert r.json() == {"spaces": len(ids), "values": ["biet_thu"]}
    assert all(_tags(s, h)["loai_cong_trinh"] == ["biet_thu"] for s in ids)
    client.put("/spaces/tags", headers=h, json={"space_ids": ids, "dimension": "loai_cong_trinh", "values": ["van_phong"]})
    assert _tags(ids[0], h)["loai_cong_trinh"] == ["van_phong"]


@pytest.mark.parametrize("body", [
    {"dimension": "phong_cach", "values": ["Japandi"]},              # mirrored from the AI columns
    {"dimension": "muc_dau_tu", "values": ["free"]},                  # unknown value
    {"dimension": "muc_dau_tu", "values": ["duoi_300tr", "tren_1500tr"]},  # single-value dimension
    {"dimension": "nope", "values": []},
])
def test_tag_refusals(as_role, drafts, body):
    h = as_role("architect")
    [sid] = drafts(1)
    assert client.put("/spaces/tags", headers=h, json={"space_ids": [sid], **body}).status_code == 422


# ── 5. hotspots ──────────────────────────────────────────────────────────────

def test_hotspots_keep_list(as_role, drafts):
    h = as_role("architect")
    [sid] = drafts(1, "jsonb_array_length(hotspots->'objects') >= 3")
    before = _space(sid, h)["hotspots"]["objects"]
    assert client.patch(f"/spaces/{sid}", headers=h, json={"hotspots": [{"index": 99, "label_vi": "x"}]}).status_code == 422
    client.patch(f"/spaces/{sid}", headers=h, json={"hotspots": [{"index": 2, "label_vi": "Kệ TV gỗ óc chó"}]})
    after = _space(sid, h)["hotspots"]["objects"]
    assert len(after) == 1 and after[0]["label_vi"] == "Kệ TV gỗ óc chó"
    assert after[0]["hotspot_anchor"] == before[2]["hotspot_anchor"]
