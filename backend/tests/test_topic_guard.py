"""Forbidden topics (change topic-guard-sitemap-item-services, seq-3 b15). The language model is switched off, so answers
come from the sample knowledge base only; every topic, conversation, lead and gap a test makes is removed afterwards."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import assistant, topic_guard as tg
from pipeline.store import DSN

KNOWN = "D3 Studio có thiết kế phòng khách không?"  # answered by the sample service entry (sofa, kệ tivi, ...)


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def topic():
    """topic(name, keywords, bat=True) -> row; all removed afterwards."""
    made = []

    def make(name, keywords, bat=True):
        with psycopg.connect(DSN) as c:
            row = tg.create(c, {"ten": f"{name} {uuid.uuid4().hex[:6]}", "tu_khoa": keywords, "bat": bat})
        made.append(row["id"])
        return row
    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM chu_de_cam WHERE id = ANY(%s)", (made,))


@pytest.fixture
def chat(monkeypatch):
    monkeypatch.setattr(assistant.vertex, "available", lambda: False)
    made, asked, leads = set(), [], []

    def send(message, hid=None):
        r = client.post("/chat", json={"message": message, **({"hoi_thoai_id": hid} if hid else {})})
        assert r.status_code == 200, r.text
        out = r.json()
        made.add(out["hoi_thoai_id"]); asked.append(message)
        if out.get("lead_id"):
            leads.append(out["lead_id"])
        return out, r.text
    yield send
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id = ANY(%s) OR hoi_thoai_id = ANY(%s)", (leads, list(made)))
        c.execute("DELETE FROM hoi_thoai WHERE id = ANY(%s)", (list(made),))
        c.execute("DELETE FROM khoang_trong_tri_thuc WHERE cau_hoi = ANY(%s)", (asked,))


# ── 1.2 matching and rules ──────────────────────────────────────────────────────
def test_matching_rules():
    t = [{"id": 1, "ten": "Đối thủ", "tu_khoa": ["công ty khác"], "bat": True},
         {"id": 2, "ten": "Thuế", "tu_khoa": ["thuế"], "bat": True},
         {"id": 3, "ten": "Tắt", "tu_khoa": ["phở"], "bat": False}]
    assert tg.matches(t, "cong ty khac lam re hon khong")[0]["id"] == 1
    assert tg.matches(t, "Bên CÔNG-TY khác báo rẻ hơn")[0]["id"] == 1
    assert tg.matches(t, "thiết kế phòng khách") is None  # "thuế" folds to "thue", never inside "thiet ke"
    assert tg.matches(t, "nấu phở") is None  # switched off


def test_validation_and_duplicate(topic):
    row = topic("Đối thủ", ["công ty khác", " Công ty khác ", ""])
    assert row["tu_khoa"] == ["công ty khác"]
    with psycopg.connect(DSN) as c:
        with pytest.raises(tg.Conflict):
            tg.create(c, {"ten": tg.norm(row["ten"]).upper(), "tu_khoa": ["x y"]})
        for bad in ({"ten": "A", "tu_khoa": []}, {"ten": "A", "tu_khoa": ["x"]}, {"ten": "", "tu_khoa": ["ok"]},
                    {"ten": "A", "tu_khoa": [f"k{i}" * 2 for i in range(31)]}):
            with pytest.raises(tg.Invalid):
                tg.create(c, bad)


# ── 1.3 the assistant ───────────────────────────────────────────────────────────
def test_question_hit_hands_off_without_gap(topic, chat):
    t = topic("Đối thủ", ["công ty khác"])
    q = f"Bên công ty khác báo rẻ hơn, D3 Studio có thiết kế phòng khách không? {uuid.uuid4().hex[:4]}"
    out, raw = chat(q)
    assert not out["answered"] and out["answer"] == assistant.FALLBACK and not out["sources"] and not out["images"]
    assert "chu_de_cam" not in out and t["ten"] not in raw and "công ty khác" not in raw.replace(q, "")
    assert _q("SELECT intent FROM lead WHERE id = %s", out["lead_id"]) == [("handoff",)]
    assert _q("SELECT count(*) FROM khoang_trong_tri_thuc WHERE cau_hoi = %s", q) == [(0,)]


def test_draft_only_hit_and_switched_off(topic, chat):
    assert chat(KNOWN)[0]["answered"]  # baseline: the sample service entry answers
    t = topic("Thiết bị", ["kệ tivi"])
    out, _ = chat(KNOWN)
    assert not out["answered"] and out["answer"] == assistant.FALLBACK
    with psycopg.connect(DSN) as c:
        tg.update(c, t["id"], {"bat": False})
    assert chat(KNOWN)[0]["answered"]


# ── 1.4 storage and API ─────────────────────────────────────────────────────────
def test_hit_stored_for_staff_only(topic, chat, as_role):
    t = topic("Đối thủ", ["công ty khác"])
    out, _ = chat(KNOWN)
    hid = out["hoi_thoai_id"]
    out, _ = chat("Công ty khác làm thế nào?", hid)
    visitor = client.get(f"/chat/{hid}")
    assert visitor.status_code == 200 and t["ten"] not in visitor.text and "chu_de_cam" not in visitor.text
    detail = client.get(f"/conversations/{hid}", headers=as_role("content")).json()
    replies = [m for m in detail["tin_nhan"] if m["vai_tro"] == "tro_ly"]
    assert replies[0]["chu_de_cam"] is None
    assert replies[1]["chu_de_cam"] == {"id": t["id"], "ten": t["ten"], "o": "cau_hoi"}
    assert detail["chua_tra_loi"] == 1


def test_roles_and_try(as_role):
    content, lead = as_role("content"), as_role("lead_architect")
    assert client.get("/forbidden-topics", headers=as_role("sales")).status_code == 403
    assert client.get("/forbidden-topics").status_code == 401
    name = f"Đối thủ {uuid.uuid4().hex[:6]}"
    r = client.post("/forbidden-topics", json={"ten": name, "tu_khoa": ["công ty khác"]}, headers=content)
    assert r.status_code == 201
    tid = r.json()["id"]
    try:
        assert client.post("/forbidden-topics", json={"ten": name.upper(), "tu_khoa": ["a b"]}, headers=content).status_code == 409
        bad = client.post("/forbidden-topics", json={"ten": "X", "tu_khoa": []}, headers=content)
        assert bad.status_code == 422 and bad.json()["detail"][0]["loc"] == ["body", "tu_khoa"]
        hit = client.post("/forbidden-topics/try", json={"text": "bên công ty khác báo rẻ hơn"}, headers=content).json()
        assert hit["trung"] == {"id": tid, "ten": name, "tu_khoa": "công ty khác"}
        assert client.patch(f"/forbidden-topics/{tid}", json={"bat": False}, headers=content).json()["bat"] is False
        assert client.delete(f"/forbidden-topics/{tid}", headers=content).status_code == 403
        assert client.delete(f"/forbidden-topics/{tid}", headers=lead).status_code == 204
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM chu_de_cam WHERE id = %s", (tid,))
