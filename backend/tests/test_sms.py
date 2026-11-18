"""visitor-touchpoints 2.4: SMS confirmations, logged with the number masked."""
import psycopg
import pytest

from conftest import client
from pipeline import notify
from pipeline.store import DSN


def _last():
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT id, lead_id, so_che, trang_thai, loi FROM tin_nhan_sms ORDER BY id DESC LIMIT 1").fetchone()


@pytest.fixture
def clean():
    with psycopg.connect(DSN) as c:
        top = c.execute("SELECT COALESCE(max(id), 0) FROM tin_nhan_sms").fetchone()[0]
    yield
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM tin_nhan_sms WHERE id > %s", (top,))


def test_not_configured_is_logged_masked(clean, monkeypatch):
    monkeypatch.delenv("D3_SMS_URL", raising=False)
    assert notify.send_sms("0912 345 678", "Xin chào", None) == "chua_cau_hinh"
    assert _last()[2:4] == ("*******678", "chua_cau_hinh")


def test_provider_ok_and_error(clean, monkeypatch):
    monkeypatch.setenv("D3_SMS_URL", "http://gateway.invalid/send")
    monkeypatch.setenv("D3_SMS_TOKEN", "t")

    class Res:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
    seen = []
    monkeypatch.setattr(notify.urllib.request, "urlopen", lambda req, timeout: seen.append(req) or Res())
    assert notify.send_sms("0912345678", "Xin chào") == "da_gui" and seen[0].get_header("Authorization") == "Bearer t"

    def boom(req, timeout):
        raise OSError("gateway down")
    monkeypatch.setattr(notify.urllib.request, "urlopen", boom)
    assert notify.send_sms("0912345678", "Xin chào") == "loi" and "gateway down" in _last()[4]


def test_contact_form_succeeds_and_logs_the_sms(clean, monkeypatch):
    monkeypatch.delenv("D3_SMS_URL", raising=False)
    r = client.post("/leads", json={"ho_ten": "Nguyễn Thử", "so_dien_thoai": "0912345678", "loi_nhan": "Tư vấn căn hộ", "t_ms": 8000})
    assert r.status_code == 201, r.text
    row = _last()
    try:
        assert row[1] == r.json()["lead_id"] and row[2:4] == ("*******678", "chua_cau_hinh")
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM lead WHERE id=%s", (r.json()["lead_id"],))
