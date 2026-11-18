"""visitor-touchpoints 2.3: act-4 working hours for chat hand-offs."""
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

import api
from conftest import client
from pipeline import hours, notify
from pipeline.store import DSN

VN = timezone(timedelta(hours=7))


@pytest.mark.parametrize("now,expected", [
    (datetime(2026, 11, 21, 21, 0, tzinfo=VN), datetime(2026, 11, 23, 8, 0, tzinfo=VN)),   # Saturday night -> Monday
    (datetime(2026, 11, 22, 10, 0, tzinfo=VN), datetime(2026, 11, 23, 8, 0, tzinfo=VN)),   # Sunday -> Monday
    (datetime(2026, 11, 24, 10, 0, tzinfo=VN), None),                                      # Tuesday morning: open
    (datetime(2026, 11, 24, 7, 30, tzinfo=VN), datetime(2026, 11, 24, 8, 0, tzinfo=VN)),   # before 08:00 the same day
    (datetime(2026, 11, 24, 17, 30, tzinfo=VN), datetime(2026, 11, 25, 8, 0, tzinfo=VN)),  # closing time -> tomorrow
])
def test_next_open(now, expected):
    assert hours.next_open(now, "T2-T7 08:00-17:30") == expected


def test_spec_parsing_and_sentence():
    assert hours.parse("T2,T4 09:00-12:00")[0] == {0, 2}
    assert hours.parse("nonsense") == hours.parse(hours.DEFAULT)
    assert hours.sentence(datetime(2026, 11, 23, 8, 0, tzinfo=VN)) == "Đội tư vấn sẽ liên hệ anh/chị từ 08:00 thứ Hai (23/11)."


@pytest.fixture
def lead():
    with psycopg.connect(DSN) as c:
        lid = c.execute("INSERT INTO lead (nguon, ho_ten, contact) VALUES ('chat', 'Thử', '0912345678') RETURNING id").fetchone()[0]
    yield lid
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id=%s", (lid,))


def test_chat_lead_at_night_is_told_and_deferred(lead, monkeypatch):
    monday = datetime(2026, 11, 23, 8, 0, tzinfo=VN)
    monkeypatch.setattr(hours, "next_open", lambda now=None, spec=None: monday)
    monkeypatch.setattr(api, "respond", lambda *a, **k: {"answer": "Em đã ghi nhận.", "sources": [], "answered": False,
                                                          "rang_buoc": {}, "lead_id": lead})
    sent = []
    monkeypatch.setattr(notify, "notify_new_lead", lambda lid: sent.append(lid))
    r = client.post("/chat", json={"message": "gọi cho tôi 0912345678"})
    assert r.status_code == 200 and r.json()["answer"].endswith("từ 08:00 thứ Hai (23/11).") and sent == []
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT thong_bao_luc, da_thong_bao FROM lead WHERE id=%s", (lead,)).fetchone() == (monday, False)
    assert notify.due_leads(monday - timedelta(minutes=1)) == []        # not yet
    assert notify.due_leads(monday + timedelta(minutes=5)) == [lead]    # the working period started
    assert notify.due_leads(monday + timedelta(minutes=15)) == []       # never twice


def test_chat_lead_in_hours_is_notified_at_once(lead, monkeypatch):
    monkeypatch.setattr(hours, "next_open", lambda now=None, spec=None: None)
    monkeypatch.setattr(api, "respond", lambda *a, **k: {"answer": "Em đã ghi nhận.", "sources": [], "answered": False,
                                                          "rang_buoc": {}, "lead_id": lead})
    sent = []
    monkeypatch.setattr(notify, "notify_new_lead", lambda lid: sent.append(lid))
    r = client.post("/chat", json={"message": "gọi cho tôi"})
    assert r.json()["answer"] == "Em đã ghi nhận." and sent == [lead]
