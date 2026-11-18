"""publishing-workflow (seq-6, act-1): the editing stage, required dimensions, hand-over emails, publish date and the
assistant's knowledge. Photos come from the drafts fixture and are put back."""
import psycopg
import pytest

from conftest import client
from pipeline import notify, space_knowledge, vertex
from pipeline.store import DSN


def _q(sql, *a):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, a).fetchall()


def _adv(sid, h, **kw):
    return client.patch(f"/spaces/{sid}", json={"advance": True, **kw}, headers=h)


def test_architect_cannot_move_editing_on(as_role, drafts):
    [sid] = drafts(1, "space_type IS NOT NULL AND design_style IS NOT NULL")
    arch = as_role("architect")
    assert _adv(sid, arch).json()["review_status"] == "editing"
    assert _adv(sid, arch).status_code == 403


def test_missing_required_dimension_is_named(as_role, drafts):
    [sid] = drafts(1)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET design_style = NULL WHERE id=%s", (sid,))
    r = _adv(sid, as_role("lead_architect"))
    assert r.status_code == 422 and r.json()["detail"]["thieu"] == ["Phong cách"] and r.json()["detail"]["msg"] == "Thiếu: Phong cách"
    assert _q("SELECT review_status FROM space WHERE id=%s", sid)[0][0] == "draft"


def test_return_from_editing(as_role, drafts):
    [sid] = drafts(1)
    lead = as_role("lead_architect")
    _adv(sid, lead)
    r = client.post("/spaces/return", json={"space_ids": [sid], "ly_do": "Thiếu ảnh toàn cảnh"}, headers=lead)
    assert r.status_code == 200 and _q("SELECT review_status, ly_do_duyet->>'ly_do' FROM space WHERE id=%s", sid)[0] == \
        ("draft", "Thiếu ảnh toàn cảnh")


@pytest.fixture
def mail(monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "_smtp_ready", lambda: True)
    monkeypatch.setattr(notify, "_send", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def test_handover_emails_once_per_action_to_the_next_role(as_role, drafts, mail):
    a, b, c = drafts(3)
    content, locked, lead = as_role("content"), as_role("content"), as_role("lead_architect")
    emails = {k: client.get("/auth/me", headers=h).json()["email"] for k, h in (("on", content), ("off", locked), ("lead", lead))}
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE app_user SET bi_khoa = true WHERE email = %s", (emails["off"],))
    assert client.post("/spaces/advance", json={"space_ids": [a, b, c]}, headers=as_role("architect")).status_code == 200
    mine = [m for m in mail if m[0] == emails["on"]]
    assert len(mine) == 1 and "Chờ biên tập" in mine[0][1] and all(f"#{x}" in mine[0][2] for x in (a, b, c))
    assert not [m for m in mail if m[0] == emails["off"]]  # a locked account gets nothing
    mail.clear()
    assert client.post("/spaces/advance", json={"space_ids": [a, b]}, headers=content).status_code == 200
    to_lead = [m for m in mail if m[0] == emails["lead"]]
    assert len(to_lead) == 1 and "Chờ duyệt" in to_lead[0][1]


def test_handover_without_email_still_moves(as_role, drafts, monkeypatch):
    monkeypatch.setattr(notify, "_smtp_ready", lambda: False)
    [sid] = drafts(1)
    assert _adv(sid, as_role("architect")).json()["review_status"] == "editing"


def test_publish_sets_the_date_queues_knowledge_and_takedown_removes_it(as_role, drafts, monkeypatch):
    [sid] = drafts(1)
    lead = as_role("lead_architect")
    for kw in ({}, {}, {}, {"rights_confirmed": True}, {}):
        assert _adv(sid, lead, **kw).status_code == 200
    row = client.get(f"/spaces/{sid}").json()
    assert row["review_status"] == "published" and row["ngay_xuat_ban"]
    task = _q("SELECT id, loai, du_lieu FROM hang_doi_tac_vu WHERE loai='nap_tri_thuc' AND du_lieu->>'space_id' = %s "
              "ORDER BY id DESC LIMIT 1", str(sid))
    assert task, "publishing queues the knowledge task"
    monkeypatch.setattr(vertex, "embed", lambda texts, kind: [[0.01] * 768 for _ in texts])
    with psycopg.connect(DSN, autocommit=True) as c:
        space_knowledge.load(c, {"id": task[0][0], "du_lieu": {"space_id": sid}}, {})
    text, model = _q("SELECT transcript, mo_hinh FROM space_text WHERE space_id=%s", sid)[0]
    style = _q("SELECT g.ten FROM space s JOIN gia_tri_phan_loai g ON g.ma_dinh_danh = s.design_style "
               "JOIN chieu_phan_loai c ON c.id = g.chieu_id AND c.ma_dinh_danh = 'phong_cach' WHERE s.id=%s", sid)
    assert model and (not style or style[0][0] in text)
    assert not space_knowledge.FORBIDDEN.search(text)
    r = client.post("/spaces/unpublish", json={"space_ids": [sid], "ly_do": "Khách rút lại đồng ý"}, headers=lead)
    assert r.status_code == 200 and _q("SELECT count(*) FROM space_text WHERE space_id=%s", sid)[0][0] == 0


def test_compose_drops_price_sentences(drafts):
    [sid] = drafts(1)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status='published', caption='Phòng khách gỗ sáng. Trọn gói 500 triệu' WHERE id=%s", (sid,))
        text = space_knowledge.compose(c, sid)
    assert "Phòng khách gỗ sáng" in text and "500 triệu" not in text


def test_backfill_queues_published_photos_once():
    with psycopg.connect(DSN) as c:
        c.execute("SAVEPOINT b")
        first = space_knowledge.backfill(c)
        assert space_knowledge.backfill(c) == 0  # already queued: not again
        c.execute("ROLLBACK TO SAVEPOINT b")
    assert first >= 0
