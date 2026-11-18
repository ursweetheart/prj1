"""Project APIs (change: project-catalog 3.1-3.2). A throw-away project 'zzt-api' with 3 spaces, removed afterwards."""

import psycopg
import pytest

from conftest import client
from pipeline.store import DSN

SLUG = "zzt-api"


@pytest.fixture
def project():
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO du_an (slug, ten, loai, thu_tu, co_trang) VALUES (%s, 'ZZT API', 'villa', 999, true)", (SLUG,))
        ids = [c.execute("INSERT INTO space (relative_path, review_status, du_an_slug, anh_trang) VALUES (%s, %s, %s, %s) "
                         "RETURNING id", (f"zzt_api_old/{name}", status, SLUG, file)).fetchone()[0]
               for name, status, file in [("b.jpg", "published", "03.jpg"), ("a.jpg", "published", "01.jpg"),
                                          ("c.jpg", "draft", None)]]
    yield ids
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (ids,))
        c.execute("DELETE FROM du_an WHERE slug = %s", (SLUG,))


def _row(rows):
    return next((r for r in rows if r["slug"] == SLUG), None)


def test_list_visitor_vs_staff(project, as_role):
    v = _row(client.get("/projects").json())
    assert v["so_anh_da_dang"] == 2 and "so_anh_chua_dang" not in v and v["anh_dai_dien"]["anh_trang"] == "01.jpg"
    s = _row(client.get("/projects", headers=as_role("architect")).json())
    assert (s["so_anh_da_dang"], s["so_anh_chua_dang"]) == (2, 1)


def test_project_without_published_photo_is_hidden_from_visitors(project, as_role):
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status = 'draft' WHERE id = ANY(%s)", (project,))
    assert _row(client.get("/projects").json()) is None
    assert client.get(f"/projects/{SLUG}").status_code == 404
    assert _row(client.get("/projects", headers=as_role("architect")).json())


def test_detail_in_site_photo_order(project, as_role):
    r = client.get(f"/projects/{SLUG}").json()
    assert r["ten"] == "ZZT API" and [s["anh_trang"] for s in r["spaces"]] == ["01.jpg", "03.jpg"]
    staff = client.get(f"/projects/{SLUG}", headers=as_role("architect")).json()
    assert [s["anh_trang"] for s in staff["spaces"]] == ["01.jpg", "03.jpg", None]


def test_unknown_and_bad_slugs():
    assert client.get("/projects/khong-co-du-an-nay").status_code == 404
    assert client.get("/projects/Bad_Slug").status_code == 422


def test_edit_details_is_validated_and_logged(project, as_role):
    lead = as_role("lead_architect")
    body = {"dien_tich_m2": 85, "so_phong_ngu": 2, "muc_dau_tu": "700tr_1500tr", "thuyet_minh": "Ánh sáng tự nhiên"}
    r = client.put(f"/projects/{SLUG}", json=body, headers=lead)
    assert r.status_code == 200 and (r.json()["dien_tich_m2"], r.json()["muc_dau_tu"]) == (85, "700tr_1500tr")
    with psycopg.connect(DSN) as c:
        log = c.execute("SELECT chi_tiet FROM nhat_ky_du_an WHERE du_an_slug = %s AND hanh_dong = 'sua'", (SLUG,)).fetchone()[0]
    assert log["truoc"]["dien_tich_m2"] is None and log["sau"]["so_phong_ngu"] == 2

    assert client.put(f"/projects/{SLUG}", json={**body, "muc_dau_tu": "rat_dat"}, headers=lead).status_code == 422
    assert client.put(f"/projects/{SLUG}", json={**body, "dien_tich_m2": 0}, headers=lead).status_code == 422
    assert client.put(f"/projects/{SLUG}", json={**body, "ten": "Đổi tên"}, headers=lead).status_code == 422  # site field
    assert client.get(f"/projects/{SLUG}").json()["muc_dau_tu"] == "700tr_1500tr"  # nothing changed by the rejects
    assert client.put(f"/projects/{SLUG}", json=body, headers=as_role("architect")).status_code == 403
    assert client.put("/projects/khong-co-du-an-nay", json=body, headers=lead).status_code == 404


def test_folder_route_also_returns_matched_spaces_with_their_site_file(project):
    """The site asks by folder (slug with '_'); spaces stored under another folder come with anh_trang."""
    rows = client.get("/projects/zzt_api/spaces").json()
    assert sorted((r["anh_trang"], r["du_an_slug"]) for r in rows) == [("01.jpg", SLUG), ("03.jpg", SLUG)]


# ── admin-tools 5.3: class-6 DuAn attributes ─────────────────────────────────────────────────────────────────────
def test_new_details_and_derived_state(project, as_role):
    lead = as_role("lead_architect")
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET ngay_xuat_ban = CASE WHEN anh_trang = '01.jpg' THEN timestamptz '2026-11-12 10:00+07' ELSE timestamptz '2026-11-18 10:00+07' END "
                  "WHERE id = ANY(%s) AND review_status = 'published'", (project,))
    r = client.put(f"/projects/{SLUG}", json={"so_ngay_thi_cong": 90, "du_an_bat_dong_san": "Vinhomes Ocean Park"}, headers=lead)
    assert r.status_code == 200
    p = client.get(f"/projects/{SLUG}").json()
    assert (p["so_ngay_thi_cong"], p["du_an_bat_dong_san"]) == (90, "Vinhomes Ocean Park")
    assert (p["trang_thai"], p["da_xac_nhan_quyen_cong_bo"]) == ("da_xuat_ban", True) and p["ngay_xuat_ban"].startswith("2026-11-1")
    assert p["ngay_xuat_ban"][:10] == "2026-11-12"  # the earliest publish date
    listed = _row(client.get("/projects").json())
    assert listed["trang_thai"] == "da_xuat_ban"
    assert client.put(f"/projects/{SLUG}", json={"so_ngay_thi_cong": 0}, headers=lead).status_code == 422


def test_unpublished_project_state(project, as_role):
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET review_status = 'draft' WHERE id = ANY(%s)", (project,))
    p = client.get(f"/projects/{SLUG}", headers=as_role("architect")).json()
    assert (p["trang_thai"], p["da_xac_nhan_quyen_cong_bo"], p["ngay_xuat_ban"]) == ("chua_xuat_ban", False, None)
