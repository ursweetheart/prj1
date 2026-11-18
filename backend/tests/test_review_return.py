"""Return to draft / keep internal / reopen (change review-return-reject). Throw-away spaces 'test_rr_*/'."""
import uuid

import psycopg
import pytest

import api
from conftest import client
from pipeline import notify
from pipeline.store import DSN


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def photos():
    """photos(status, n=1, uploader_id=None) -> ids of throw-away spaces; an 'ingest' log row names the uploader."""
    made = []

    def make(status, n=1, uploader_id=None):
        ids = []
        with psycopg.connect(DSN) as c:
            for _ in range(n):
                sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status) "
                                "VALUES (%s, 'phong_khach', 'Japandi', %s) RETURNING id",
                                (f"test_rr_{uuid.uuid4().hex[:6]}/x.jpg", status)).fetchone()[0]
                if uploader_id:
                    c.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, %s, 'ingest', '{}')",
                              (sid, uploader_id))
                ids.append(sid)
        made.extend(ids)
        return ids

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made,))


def _status(sid):
    return _q("SELECT review_status, ly_do_duyet FROM space WHERE id=%s", sid)[0]


def _me(headers):
    return client.get("/auth/me", headers=headers).json()


REASON = "Nhãn phong cách sai, đây là Japandi"


# ── 1.1 endpoints ──────────────────────────────────────────────────────────────
def test_return_from_each_review_step(photos, as_role):
    lead = as_role("lead_architect")
    ids = photos("in_review") + photos("approved") + photos("cleared")
    r = client.post("/spaces/return", json={"space_ids": ids, "ly_do": "  " + REASON + " "}, headers=lead)
    assert r.status_code == 200 and r.json() == {"moved": sorted(ids), "status": "draft"}
    for sid in ids:
        st, shown = _status(sid)
        assert st == "draft" and shown["loai"] == "tra_ve" and shown["ly_do"] == REASON
        assert shown["boi"] == _me(lead)["email"] and shown["luc"]
    act, detail = _q("SELECT action, detail FROM review_log WHERE space_id=%s ORDER BY id DESC LIMIT 1", ids[1])[0]
    assert act == "return" and detail == {"from": "approved", "to": "draft", "reason": REASON}


def test_refusals_move_nothing(photos, as_role):
    lead = as_role("lead_architect")
    ok, pub, draft, internal = photos("in_review")[0], photos("published")[0], photos("draft")[0], photos("noi_bo")[0]
    for other in (pub, draft, internal):
        r = client.post("/spaces/return", json={"space_ids": [ok, other], "ly_do": REASON}, headers=lead)
        assert r.status_code == 409 and str(other) in r.json()["detail"]
    assert _status(ok)[0] == "in_review" and _status(ok)[1] is None
    assert client.post("/spaces/return", json={"space_ids": [ok], "ly_do": " sai "}, headers=lead).status_code == 422
    assert client.post("/spaces/return", json={"space_ids": [ok, 99999999], "ly_do": REASON}, headers=lead).status_code == 404
    assert _status(ok)[0] == "in_review"


def test_roles(photos, as_role):
    sid = photos("in_review")[0]
    for role in ("architect", "content", "sales", "visitor"):
        h = as_role(role)  # one account per role (registering is rate limited)
        for path in ("/spaces/return", "/spaces/keep-internal", "/spaces/reopen"):
            assert client.post(path, json={"space_ids": [sid], "ly_do": REASON}, headers=h).status_code == 403
    assert client.post("/spaces/return", json={"space_ids": [sid], "ly_do": REASON}).status_code == 401
    assert _status(sid)[0] == "in_review"


def test_keep_internal_is_final_hidden_and_reopens(photos, as_role):
    lead = as_role("lead_architect")
    sid = photos("approved")[0]
    assert client.post("/spaces/keep-internal", json={"space_ids": [sid], "ly_do": "Khách không đồng ý công bố"},
                       headers=lead).json()["status"] == "noi_bo"
    assert _status(sid)[1]["loai"] == "noi_bo"
    assert client.patch(f"/spaces/{sid}", json={"advance": True}, headers=lead).status_code == 409
    assert client.post("/spaces/advance", json={"space_ids": [sid]}, headers=lead).status_code == 409
    assert client.get(f"/spaces/{sid}").status_code == 404                     # not public
    assert sid not in [s["id"] for s in client.get("/spaces", params={"limit": 200}).json()]
    assert client.post("/spaces/keep-internal", json={"space_ids": photos("in_review")}, headers=lead).status_code == 422  # no reason
    assert client.post("/spaces/keep-internal", json={"space_ids": photos("in_review"), "ly_do": REASON},
                       headers=lead).status_code == 409                       # only from approved / cleared
    r = client.post("/spaces/reopen", json={"space_ids": [sid], "ly_do": "Khách đã đồng ý lại"}, headers=lead)
    assert r.json()["status"] == "draft" and _status(sid)[1]["loai"] == "mo_lai"


def test_reason_cleared_on_advance_kept_in_log_and_filter(photos, as_role):
    lead, arch = as_role("lead_architect"), as_role("architect")
    returned, plain = photos("in_review")[0], photos("draft")[0]
    client.post("/spaces/return", json={"space_ids": [returned], "ly_do": REASON}, headers=lead)
    listed = client.get("/spaces", params={"review_status": "draft", "tra_ve": 1, "limit": 200}, headers=arch).json()
    ids = [s["id"] for s in listed]
    assert returned in ids and plain not in ids
    assert next(s for s in listed if s["id"] == returned)["ly_do_duyet"]["ly_do"] == REASON
    public = client.get("/spaces", params={"limit": 5, "tra_ve": 1}).json()
    assert all("ly_do_duyet" not in s for s in public)                         # staff-only field
    assert client.patch(f"/spaces/{returned}", json={"advance": True}, headers=arch).status_code == 200
    assert _status(returned) == ("editing", None)  # publishing-workflow: drafts go to "Chờ biên tập"
    assert _q("SELECT count(*) FROM review_log WHERE space_id=%s AND action='return' AND detail->>'reason'=%s",
              returned, REASON)[0][0] == 1


# ── 1.2 notice to the uploader ─────────────────────────────────────────────────
def test_one_message_per_uploader(photos, as_role, monkeypatch):
    lead, arch = as_role("lead_architect"), as_role("architect")
    me = _me(arch)
    a, b = photos("in_review", 2, uploader_id=me["id"])
    orphan = photos("in_review")[0]
    sent, logged = [], []
    monkeypatch.setattr(notify, "_smtp_ready", lambda: True)
    monkeypatch.setattr(notify, "_send", lambda to, subject, body: sent.append((to, subject, body)))
    monkeypatch.setattr(notify.review_log, "info", lambda *a: logged.append(a[0] % a[1:]))
    r = client.post("/spaces/return", json={"space_ids": [a, b, orphan], "ly_do": REASON}, headers=lead)
    assert r.status_code == 200
    assert len(sent) == 1 and sent[0][0] == me["email"] and "2 ảnh" in sent[0][1]
    assert f"#{a}" in sent[0][2] and f"#{b}" in sent[0][2] and sent[0][2].count(REASON) == 2
    assert len(logged) == 1 and f"#{orphan}" in logged[0] and "không rõ người tải lên" in logged[0]


def test_failing_mail_does_not_undo(photos, as_role, monkeypatch):
    lead, arch = as_role("lead_architect"), as_role("architect")
    sid = photos("in_review", uploader_id=_me(arch)["id"])[0]
    monkeypatch.setattr(notify, "_smtp_ready", lambda: True)

    def boom(*a):
        raise OSError("smtp down")
    monkeypatch.setattr(notify, "_send", boom)
    r = client.post("/spaces/return", json={"space_ids": [sid], "ly_do": REASON}, headers=lead)
    assert r.status_code == 200 and _status(sid)[0] == "draft"
    assert api.notify is notify  # the endpoint uses the same module the test patched
