"""Weekly report (change weekly-report). Mail is never sent: notify._send is replaced by a collector. Counts are checked as
differences against real data, as in test_trends. Test weeks in bao_cao_tuan are far in the past and removed afterwards."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from conftest import client
from pipeline import notify, weekly_report as wr
from pipeline.store import DSN

VN = wr.VN
# a Wednesday long ago, so the claimed week (2001-03-05) never collides with a real one
OLD = datetime(2001, 3, 14, 10, 0, tzinfo=VN)


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def mail(monkeypatch):
    """Collects (to, subject, body) instead of sending; SMTP looks configured."""
    sent = []
    monkeypatch.setenv("D3_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(notify, "_send", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


@pytest.fixture
def weeks():
    taken = []
    yield taken
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM bao_cao_tuan WHERE tuan_bat_dau < '2002-01-01'")


@pytest.fixture
def people():
    """people(role, **cols) -> email of a throw-away account; removed afterwards."""
    made = []

    def make(role, email=None, **cols):
        email = email or f"wr-{uuid.uuid4().hex[:8]}@example.com"
        with psycopg.connect(DSN) as c:
            uid = c.execute("INSERT INTO app_user (email, role) VALUES (%s, %s) RETURNING id", (email, role)).fetchone()[0]
            for k, v in cols.items():
                c.execute(f"UPDATE app_user SET {k}=%s WHERE id=%s", (v, uid))
        made.append(uid)
        return email

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM app_user WHERE id = ANY(%s)", (made,))


@pytest.fixture
def activity():
    """A published space and a consented session; events(loai, n, at) dated exactly; removed afterwards."""
    with psycopg.connect(DSN) as c:
        sid = c.execute("INSERT INTO space (relative_path, review_status) VALUES (%s, 'published') RETURNING id",
                        (f"test_wr_{uuid.uuid4().hex[:8]}/x.jpg",)).fetchone()[0]
        pid = "t" + uuid.uuid4().hex
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
    leads = []

    def events(loai, n, at):
        with psycopg.connect(DSN) as c:
            for _ in range(n):
                c.execute("INSERT INTO su_kien (phien_id, loai, space_id, created_at) VALUES (%s,%s,%s,%s)", (pid, loai, sid, at))

    def lead(at):
        with psycopg.connect(DSN) as c:
            leads.append(c.execute("INSERT INTO lead (nguon, ho_ten, so_dien_thoai, email, created_at, phien_id) VALUES "
                                   "('form', 'Nguyễn Văn Thử', '0912345678', 'thu@example.com', %s, %s) RETURNING id",
                                   (at, pid)).fetchone()[0])

    yield type("A", (), {"events": staticmethod(events), "lead": staticmethod(lead), "pid": pid})
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE id = ANY(%s)", (leads,))
        c.execute("DELETE FROM phien_truy_cap WHERE id = %s", (pid,))
        c.execute("DELETE FROM space WHERE id = %s", (sid,))


def _build(now):
    with psycopg.connect(DSN) as c:
        return wr.build(c, now)


def _send(now, **kw):
    with psycopg.connect(DSN) as c:
        return wr.send_week(c, now, **kw)


# ── 1.2 week, schedule, content ─────────────────────────────────────────────────
def test_week_bounds_in_vietnam_time():
    start, end = wr.week_bounds(datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc))  # Wednesday
    assert (start, end) == (datetime(2026, 11, 9, tzinfo=VN), datetime(2026, 11, 16, tzinfo=VN))
    # Sunday 23:30 in Vietnam is Sunday 16:30 UTC: still the week that started Monday 9th
    s2, _ = wr.week_bounds(datetime(2026, 11, 15, 16, 30, tzinfo=timezone.utc))
    assert s2 == datetime(2026, 11, 2, tzinfo=VN)
    # Monday 00:30 in Vietnam is Sunday 17:30 UTC: the new week has begun
    s3, _ = wr.week_bounds(datetime(2026, 11, 15, 17, 30, tzinfo=timezone.utc))
    assert s3 == datetime(2026, 11, 9, tzinfo=VN)


def test_due_from_monday_eight():
    assert not wr.due(datetime(2026, 11, 16, 7, 30, tzinfo=VN))
    assert wr.due(datetime(2026, 11, 16, 8, 0, tzinfo=VN))
    assert wr.due(datetime(2026, 11, 17, 10, 0, tzinfo=VN))
    assert wr.due(datetime(2026, 11, 22, 23, 59, tzinfo=VN))


def test_change_text():
    assert (wr.change(120, 100), wr.change(80, 100), wr.change(5, 0), wr.change(0, 0), wr.change(7, 7)) == \
           ("+20%", "-20%", "mới", "–", "0%")


def test_totals_by_exact_week(activity):
    start, end = wr.week_bounds(OLD)
    with psycopg.connect(DSN) as c:
        before_cur, before_prev = wr._totals(c, start, end), wr._totals(c, start - timedelta(days=7), start)
    activity.events("xem_khong_gian", 120, start + timedelta(hours=1))
    activity.events("xem_khong_gian", 100, start - timedelta(days=3))
    activity.events("luu_anh", 4, end - timedelta(minutes=1))   # last minute of Sunday: this week
    activity.events("luu_anh", 9, end)                          # Monday 00:00: next week, not counted
    with psycopg.connect(DSN) as c:
        cur, prev = wr._totals(c, start, end), wr._totals(c, start - timedelta(days=7), start)
    assert cur["luot_xem"] - before_cur["luot_xem"] == 120
    assert prev["luot_xem"] - before_prev["luot_xem"] == 100
    assert cur["luot_luu"] - before_cur["luot_luu"] == 4


def test_report_text(activity):
    start, _ = wr.week_bounds(OLD)
    activity.events("xem_khong_gian", 120, start + timedelta(hours=1))
    activity.events("xem_khong_gian", 100, start - timedelta(days=3))
    activity.lead(start + timedelta(days=1))
    r = _build(OLD)
    body = r["noi_dung"]
    assert r["tuan_bat_dau"] == start.date() and r["tieu_de"] == "[D3] Báo cáo tuần 05/03 – 11/03/2001"
    for heading in ("TỔNG QUAN", "CẢNH BÁO XU HƯỚNG", "ĐƯỢC QUAN TÂM NHẤT", "DỰ ÁN CẦN XEM LẠI", "/quan-tri/xu-huong",
                    "/quan-tri/hieu-qua", "Nhận báo cáo tuần qua email"):
        assert heading in body
    assert "Lượt xem: 120 (+20%)" in body  # nothing else happened in 2001
    assert "Form liên hệ: 1 (mới)" in body
    for secret in ("Nguyễn Văn Thử", "0912345678", "thu@example.com", activity.pid):
        assert secret not in body


def test_empty_sections_say_so(monkeypatch):
    from pipeline import project_stats, trends
    monkeypatch.setattr(trends, "overview", lambda c, d: {"canh_bao": [], "chieu": [], "co_du_lieu_mo_phong": False})
    monkeypatch.setattr(project_stats, "overview", lambda c, d: {"projects": []})
    body = _build(OLD)["noi_dung"]
    assert "Không có giá trị nào tăng hay giảm rõ rệt." in body
    assert "Không có dự án nào cần xem lại." in body
    assert "Phong cách: Không có hoạt động." in body
    assert "MÔ PHỎNG" not in body


def test_alerts_are_capped(monkeypatch):
    from pipeline import trends
    alerts = [{"chieu": "Phong cách", "ten": f"V{i}", "ma": f"v{i}", "xu_huong": "moi_noi", "thay_doi": None} for i in range(11)]
    monkeypatch.setattr(trends, "overview", lambda c, d: {"canh_bao": alerts, "chieu": [], "co_du_lieu_mo_phong": False})
    body = _build(OLD)["noi_dung"]
    assert "Phong cách · V7" in body and "Phong cách · V8" not in body and "… và 3 cảnh báo khác" in body


def test_demo_note_follows_demo_sessions():
    pid = "demo-" + uuid.uuid4().hex
    had = _q("SELECT EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%%')")[0][0]
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true)", (pid,))
    try:
        assert _build(OLD)["noi_dung"].startswith("LƯU Ý")
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM phien_truy_cap WHERE id = %s", (pid,))
    if not had:
        assert not _build(OLD)["noi_dung"].startswith("LƯU Ý")


# ── 1.3 recipients and sending ──────────────────────────────────────────────────
def test_recipients(people):
    on = [people("sales"), people("lead_architect"), people("admin")]
    off = [people("sales", bi_khoa=True), people("lead_architect", nhan_bao_cao_tuan=False), people("architect"),
           people("visitor"), people("content"), people("sales", email=f"facebook-{uuid.uuid4().hex[:6]}@facebook.invalid")]
    with psycopg.connect(DSN) as c:
        got = wr.recipients(c)
    assert all(e in got for e in on) and not any(e in got for e in off)


def test_each_recipient_gets_one_message_once(mail, people, weeks):
    a, b = people("sales"), people("admin")
    row = _send(OLD)
    to = [m[0] for m in mail]
    assert to.count(a) == 1 and to.count(b) == 1 and all(len([t]) == 1 for t in to)
    assert row["ket_qua"] == "da_gui" and row["so_nguoi_nhan"] == len(to) and row["so_loi"] == 0
    assert _send(OLD) is None and len(mail) == len(to)  # second time: nothing
    assert _q("SELECT count(*) FROM bao_cao_tuan WHERE tuan_bat_dau = '2001-03-05'")[0][0] == 1


def test_without_smtp_only_logs(monkeypatch, weeks, caplog):
    monkeypatch.delenv("D3_SMTP_HOST", raising=False)
    sent = []
    monkeypatch.setattr(notify, "_send", lambda *a: sent.append(a))
    with caplog.at_level(logging.INFO, logger="d3.report"):
        row = _send(OLD)
    assert row["ket_qua"] == "chi_ghi_log" and not sent
    assert "TỔNG QUAN" in caplog.text
    assert _q("SELECT noi_dung FROM bao_cao_tuan WHERE tuan_bat_dau = '2001-03-05'")[0][0].count("TỔNG QUAN") == 1


def test_one_failure_does_not_stop_the_others(monkeypatch, people, weeks):
    bad = people("sales")
    good = people("admin")
    sent = []
    monkeypatch.setenv("D3_SMTP_HOST", "smtp.example.com")

    def send(to, subject, body):
        if to == bad:
            raise OSError("mailbox unavailable")
        sent.append(to)
    monkeypatch.setattr(notify, "_send", send)
    row = _send(OLD)
    assert good in sent and bad not in sent
    assert row["ket_qua"] == "loi_mot_phan" and row["so_loi"] == 1


def test_test_copy_is_not_the_weeks_report(mail, people, weeks):
    me = people("lead_architect")
    out = _send(OLD, force_to=me)
    assert out == {"gui_toi": me} and [m[0] for m in mail] == [me] and mail[0][1].startswith("[Gửi thử]")
    assert _q("SELECT count(*) FROM bao_cao_tuan WHERE tuan_bat_dau = '2001-03-05'")[0][0] == 0
    assert _send(OLD)["ket_qua"] == "da_gui"


# ── 1.5 endpoints ───────────────────────────────────────────────────────────────
def test_opt_in_endpoint(as_role):
    h = as_role("sales")
    me = client.get("/auth/me", headers=h).json()["email"]
    assert client.get("/me/weekly-report", headers=h).json() == {"nhan": True}
    assert client.put("/me/weekly-report", json={"nhan": False}, headers=h).json() == {"nhan": False}
    with psycopg.connect(DSN) as c:
        assert me not in wr.recipients(c)
    client.put("/me/weekly-report", json={"nhan": True}, headers=h)
    with psycopg.connect(DSN) as c:
        assert me in wr.recipients(c)


def test_endpoint_roles(as_role):
    for role in ("visitor", "architect", "content"):
        h = as_role(role)
        assert client.get("/me/weekly-report", headers=h).status_code == 403
        assert client.put("/me/weekly-report", json={"nhan": True}, headers=h).status_code == 403
        for path in ("/reports/weekly", "/reports/weekly/preview"):
            assert client.get(path, headers=h).status_code == 403
        assert client.post("/reports/weekly/test", headers=h).status_code == 403
    sales = as_role("sales")
    assert client.get("/reports/weekly", headers=sales).status_code == 403
    assert client.get("/reports/weekly/preview", headers=sales).status_code == 403
    assert client.post("/reports/weekly/test", headers=sales).status_code == 403
    assert client.get("/reports/weekly").status_code == 401
    assert client.get("/me/weekly-report").status_code == 401


def test_preview_and_history(as_role, weeks, monkeypatch):
    monkeypatch.delenv("D3_SMTP_HOST", raising=False)
    h = as_role("lead_architect")
    p = client.get("/reports/weekly/preview", headers=h).json()
    assert p["tieu_de"].startswith("[D3] Báo cáo tuần") and "TỔNG QUAN" in p["noi_dung"] and p["nguoi_nhan"] >= 1
    for i in range(10):
        _send(OLD - timedelta(days=7 * i))
    rows = client.get("/reports/weekly", headers=h).json()
    assert len(rows) <= 8 and all("noi_dung" not in r for r in rows)
    assert [r["tuan_bat_dau"] for r in rows] == sorted((r["tuan_bat_dau"] for r in rows), reverse=True)


def test_test_send_endpoint(as_role, mail, monkeypatch):
    h = as_role("admin")
    me = client.get("/auth/me", headers=h).json()["email"]
    r = client.post("/reports/weekly/test", headers=h)
    assert r.status_code == 200 and [m[0] for m in mail] == [me]
    monkeypatch.delenv("D3_SMTP_HOST")
    assert client.post("/reports/weekly/test", headers=as_role("admin")).status_code == 409
