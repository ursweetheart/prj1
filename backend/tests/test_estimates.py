"""Cost estimate and price table D8 (change cost-estimate). Edited prices are put back to their seed values."""
import json

import psycopg
import pytest

from conftest import client
from pipeline import estimate, notify
from pipeline.store import DSN

APT = {"loai_nha": "can_ho", "dien_tich_m2": 70, "so_phong_ngu": 3, "goi": "tieu_chuan"}
CONTACT = {"ho_ten": "Lan", "so_dien_thoai": "0912345678", "email": "lan@example.com", "t_ms": 8000}
SPEC_PRICES = {"thiet_ke": (200_000, 300_000, "mau"), "phan_tho": (1_200_000, 1_800_000, "mau"),
               "hoan_thien": (2_200_000, 3_500_000, "mau"), "noi_that": (3_000_000, 5_000_000, "mau")}


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def restore_prices():
    """Snapshot don_gia and put it back after the test."""
    rows = _q("SELECT id, gia_min, gia_max, nguon, ghi_chu, cap_nhat_boi FROM don_gia")
    yield
    with psycopg.connect(DSN) as c:
        for r in rows:
            c.execute("UPDATE don_gia SET gia_min=%s, gia_max=%s, nguon=%s, ghi_chu=%s, cap_nhat_boi=%s WHERE id=%s",
                      (*r[1:], r[0]))


@pytest.fixture
def no_mail(monkeypatch):
    calls = []
    monkeypatch.setattr(notify, "notify_new_lead", lambda i: calls.append(("sales", i)))
    monkeypatch.setattr(notify, "confirm_to_visitor", lambda i: calls.append(("visitor", i)))
    return calls


@pytest.fixture
def cleanup():
    yield
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE nguon IN ('estimate', 'form') AND so_dien_thoai = '0912345678'")


def _price_id(loai, hang, goi):
    return _q("SELECT id FROM don_gia WHERE loai_nha=%s AND hang_muc=%s AND goi=%s", loai, hang, goi)[0][0]


# ── 1.1 table and seed ─────────────────────────────────────────────────────────
def test_seed_is_complete_and_sample(restore_prices):
    assert _q("SELECT count(*), bool_and(gia_min <= gia_max), count(DISTINCT (loai_nha, hang_muc, goi)) FROM don_gia")[0] \
        == (60, True, 60)
    got = dict((r[0], (r[1], r[2])) for r in _q(
        "SELECT hang_muc, gia_min, gia_max FROM don_gia WHERE loai_nha='can_ho' AND goi='tieu_chuan'"))
    assert got == {k: v[:2] for k, v in SPEC_PRICES.items()}


def test_reapplying_the_seed_keeps_staff_prices(restore_prices):
    pid = _price_id("can_ho", "hoan_thien", "tieu_chuan")
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE don_gia SET gia_min=2500000, gia_max=3800000, nguon='d3' WHERE id=%s", (pid,))
        seed = open("schema.sql").read()
        c.execute(seed[seed.index("INSERT INTO don_gia"):].split(";")[0])  # the seed statement alone
    assert _q("SELECT gia_min, gia_max, nguon FROM don_gia WHERE id=%s", pid)[0] == (2500000, 3800000, "d3")


# ── 2.1 formula and formatting ─────────────────────────────────────────────────
def test_spec_example_is_exact():
    r = estimate.compute(SPEC_PRICES, 70, 3)
    assert [(l["ma"], l["min"], l["max"]) for l in r["hang_muc"]] == [
        ("thiet_ke", 14_000_000, 21_000_000), ("phan_tho", 84_000_000, 126_000_000),
        ("hoan_thien", 154_000_000, 245_000_000), ("noi_that", 226_800_000, 378_000_000)]
    assert r["tong"] == {"min": 478_800_000, "max": 770_000_000} and r["mau"] is True


def test_two_bedrooms_no_uplift_and_staff_rows_not_sample():
    prices = {k: (lo, hi, "d3") for k, (lo, hi, _) in SPEC_PRICES.items()}
    r = estimate.compute(prices, 70, 2)
    assert r["hang_muc"][3]["min"] == 210_000_000 and r["mau"] is False
    assert estimate.compute(prices, 70, 0)["hang_muc"][3]["min"] == 210_000_000  # fewer rooms never lowers it


def test_vnd_format():
    assert estimate.vnd(478_800_000) == "478,8 triệu"
    assert estimate.vnd(770_000_000) == "770 triệu"
    assert estimate.vnd(1_250_000_000) == "1,25 tỷ"
    assert estimate.vnd(2_000_000_000) == "2 tỷ"
    assert estimate.vnd_range({"min": 478_800_000, "max": 770_000_000}) == "478,8 triệu – 770 triệu"


# ── 2.2 endpoints ──────────────────────────────────────────────────────────────
def test_estimate_endpoint(restore_prices):
    r = client.post("/estimates", json=APT)
    assert r.status_code == 200 and r.json()["tong"] == {"min": 478_800_000, "max": 770_000_000}
    assert [l["ten"] for l in r.json()["hang_muc"]] == ["Thiết kế", "Phần thô & cải tạo", "Hoàn thiện", "Nội thất"]
    assert client.post("/estimates", json={**APT, "dien_tich_m2": 5}).status_code == 422
    assert client.post("/estimates", json={**APT, "loai_nha": "lau_dai"}).status_code == 422


def test_send_recomputes_and_stores_lead(no_mail, cleanup):
    r = client.post("/estimates/send", json={**APT, **CONTACT, "tong": {"min": 1, "max": 1}})
    assert r.status_code == 201 and r.json()["message"] == "Đã gửi bản ước tính chi tiết tới lan@example.com"
    nguon, req = _q("SELECT nguon, request FROM lead WHERE id=%s", r.json()["lead_id"])[0]
    assert nguon == "estimate" and req["dau_vao"] == {**APT, "dien_tich_m2": 70.0}
    assert req["ket_qua"]["tong"] == {"min": 478_800_000, "max": 770_000_000}
    assert no_mail == [("sales", r.json()["lead_id"]), ("visitor", r.json()["lead_id"])]


def test_send_needs_email_and_traps_bots(no_mail, cleanup):
    r = client.post("/estimates/send", json={**APT, **CONTACT, "email": ""})
    assert r.status_code == 422 and any(e["loc"][-1] == "email" for e in r.json()["detail"])
    assert client.post("/estimates/send", json={k: v for k, v in {**APT, **CONTACT}.items() if k != "email"}).status_code == 422
    before = _q("SELECT count(*) FROM lead")[0][0]
    r = client.post("/estimates/send", json={**APT, **CONTACT, "website": "spam"})
    assert r.status_code == 201 and r.json()["lead_id"] is None
    assert _q("SELECT count(*) FROM lead")[0][0] == before and no_mail == []


def test_estimates_share_the_lead_limit(no_mail, cleanup):
    codes = [client.post("/leads", json={"ho_ten": "Lan", "so_dien_thoai": "0912345678", "t_ms": 8000}).status_code
             for _ in range(3)]
    codes += [client.post("/estimates/send", json={**APT, **CONTACT}).status_code for _ in range(3)]
    assert codes == [201] * 5 + [429]


# ── 2.3 price table API ────────────────────────────────────────────────────────
def test_staff_edit_is_used_at_once(restore_prices, as_role):
    lead_arch = as_role("lead_architect")
    rows = client.get("/prices", headers=lead_arch).json()
    assert len(rows) == 60 and {r["nguon"] for r in rows} == {"mau"}
    pid = _price_id("can_ho", "noi_that", "tieu_chuan")
    r = client.put(f"/prices/{pid}", json={"gia_min": 4_000_000, "gia_max": 6_000_000}, headers=lead_arch)
    assert r.status_code == 200 and r.json()["nguon"] == "d3"
    who = _q("SELECT u.email FROM don_gia g JOIN app_user u ON u.id = g.cap_nhat_boi WHERE g.id=%s", pid)[0][0]
    assert who.endswith("@example.com")
    est = client.post("/estimates", json={**APT, "so_phong_ngu": 2}).json()
    assert est["hang_muc"][3]["min"] == 280_000_000 and est["mau"] is True  # 3 other rows are still samples


def test_invalid_ranges_and_roles(restore_prices, as_role):
    pid = _price_id("biet_thu", "noi_that", "cao_cap")
    lead_arch = as_role("lead_architect")
    assert client.put(f"/prices/{pid}", json={"gia_min": 9, "gia_max": 8}, headers=lead_arch).status_code == 422
    assert client.put(f"/prices/{pid}", json={"gia_min": -1, "gia_max": 8}, headers=lead_arch).status_code == 422
    assert client.put(f"/prices/{pid}", json={"gia_min": 1, "gia_max": 8}, headers=as_role("sales")).status_code == 403
    assert client.get("/prices").status_code == 401
    assert client.put("/prices/999999", json={"gia_min": 1, "gia_max": 2}, headers=lead_arch).status_code == 404


# ── 2.4 notices and the leads list ─────────────────────────────────────────────
def test_estimate_emails(monkeypatch, cleanup):
    from test_leads import FakeSMTP
    from pipeline import leads
    with psycopg.connect(DSN) as c:
        res = estimate.estimate(c, "can_ho", 70, 3, "tieu_chuan")
    lid = leads.create_lead("estimate", ho_ten="Lan", so_dien_thoai="0912345678", email="lan@example.com",
                            request={"dau_vao": {**APT, "dien_tich_m2": 70.0}, "ket_qua": res})
    FakeSMTP.sent = []
    monkeypatch.setenv("D3_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("D3_SALES_EMAIL", "sales@example.com")
    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)
    notify.notify_new_lead(lid)
    notify.confirm_to_visitor(lid)
    sales, visitor = FakeSMTP.sent
    for body in (sales.get_content(), visitor.get_content()):
        assert "Căn hộ / Chung cư · 70 m² · 3 phòng ngủ · Tiêu chuẩn" in body and "478,8 triệu – 770 triệu" in body
        assert all(n in body for n in ("Thiết kế", "Phần thô & cải tạo", "Hoàn thiện", "Nội thất"))
        assert estimate.NOTICE in body and estimate.SAMPLE_NOTICE in body
    assert "Ước tính chi phí" in sales["Subject"] and visitor["Subject"] == "Bản ước tính chi phí từ D3 Studio"


def test_leads_filter_estimate(no_mail, cleanup, as_role):
    lid = client.post("/estimates/send", json={**APT, **CONTACT}).json()["lead_id"]
    rows = client.get("/leads", params={"nguon": "estimate"}, headers=as_role("sales")).json()
    assert {r["nguon"] for r in rows} == {"estimate"}
    assert next(r for r in rows if r["id"] == lid)["request"]["ket_qua"]["mau"] is True


# ── 2.5 chat ───────────────────────────────────────────────────────────────────
def test_price_answer_points_to_the_estimate(cleanup):
    out = client.post("/chat", json={"message": "chung cư 70m2 làm nội thất hết bao nhiêu"}).json()
    assert "/uoc-tinh" in out["answer"]
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM lead WHERE conversation @> %s::jsonb",
                  (json.dumps([{"content": "chung cư 70m2 làm nội thất hết bao nhiêu"}]),))
