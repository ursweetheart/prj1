"""tracking-pipeline 5.1: homepage "Đang được quan tâm" (act-3). Settings are saved and restored around each test."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import home_suggestions
from pipeline.store import DSN


@pytest.fixture
def clean():
    made = {"spaces": [], "sessions": []}
    with psycopg.connect(DSN) as c:
        saved = c.execute("SELECT gia_tri, che_do, nguoi_id, luc FROM goi_y_trang_chu").fetchall()
        c.execute("DELETE FROM goi_y_trang_chu")

    def space(style):
        with psycopg.connect(DSN) as c:
            sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status) VALUES (%s, 'phong_khach', %s, "
                            "'published') RETURNING id", (f"test_hs_{uuid.uuid4().hex[:8]}/x.jpg", style)).fetchone()[0]
        made["spaces"].append(sid)
        return sid

    def session(personal, views):
        pid = "ths" + uuid.uuid4().hex
        with psycopg.connect(DSN) as c:
            c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap, ca_nhan_hoa) VALUES (%s, true, %s)", (pid, personal))
            for sid in views:
                c.execute("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri) SELECT %s, 'xem_khong_gian', s.id, "
                          "ARRAY(SELECT d.ma_dinh_danh || ':' || v.ma_dinh_danh FROM space_gia_tri sg JOIN gia_tri_phan_loai v "
                          "ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE sg.space_id = s.id) "
                          "FROM space s WHERE s.id = %s", (pid, sid))
        made["sessions"].append(pid)
        return pid

    yield type("C", (), {"space": staticmethod(space), "session": staticmethod(session)})
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM goi_y_trang_chu")
        for row in saved:
            c.execute("INSERT INTO goi_y_trang_chu (gia_tri, che_do, nguoi_id, luc) VALUES (%s,%s,%s,%s)", row)
        c.execute("DELETE FROM goi_y_trang_chu_nhat_ky WHERE gia_tri LIKE 'phong_cach:%%' AND luc > now() - interval '5 minutes' "
                  "AND nguoi_id IS NULL")
        c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (made["sessions"],))
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made["spaces"],))


def _get(**params):
    r = client.get("/home/suggestions", params=params)
    assert r.status_code == 200
    return r.json()


def _set(value, mode):
    with psycopg.connect(DSN) as c:
        home_suggestions.set_mode(c, value, mode, None)


def test_prioritised_first_hidden_never_two_per_value_eight_in_all(clean):
    for _ in range(3):
        clean.space("Indochine")
    _set("phong_cach:Indochine", "uu_tien")
    _set("phong_cach:Luxury", "an")
    out = _get()
    assert [s["ly_do"]["ma"] for s in out[:2]] == ["Indochine", "Indochine"] and out[0]["ly_do"]["nguon"] == "uu_tien"
    assert out[0]["nhan"] == "Phong cách Indochine đang được quan tâm"
    assert len(out) <= 8 and all(s["ly_do"]["ma"] != "Luxury" for s in out if s["ly_do"]["chieu"] == "phong_cach")
    per = {}
    for s in out:
        per[(s["ly_do"]["chieu"], s["ly_do"]["ma"])] = per.get((s["ly_do"]["chieu"], s["ly_do"]["ma"]), 0) + 1
    assert max(per.values()) <= 2 and all(s["ly_do"]["ma"].lower() != "khac" for s in out)
    assert len({s["id"] for s in out}) == len(out)


def test_personal_order_only_with_personalisation_consent(clean):
    a, b, c3 = (clean.space("Japandi") for _ in range(3))
    yes = clean.session(True, [a, a, b, a])
    no = clean.session(False, [a, a, b, a])
    mine = _get(phien_id=yes)
    assert mine[0]["ly_do"]["nguon"] == "ca_nhan" and mine[0]["nhan"].startswith("Vì bạn đã xem")
    assert a not in {s["id"] for s in mine} and b not in {s["id"] for s in mine}  # never what they already viewed
    assert _get(phien_id=no) == _get()  # analytics only: same as everyone


def test_settings_endpoint_roles_log_and_unknown_value(clean, as_role):
    sales = as_role("sales")
    r = client.put("/analytics/home-suggestions", json={"gia_tri": "phong_cach:Japandi", "che_do": "uu_tien"}, headers=sales)
    assert r.status_code == 200
    view = client.get("/analytics/home-suggestions", headers=sales).json()
    assert view["cai_dat"][0]["gia_tri"] == "phong_cach:Japandi" and view["cai_dat"][0]["boi"]
    assert view["xem_truoc"] and view["xem_truoc"][0]["ly_do"]["ma"] == "Japandi"
    with psycopg.connect(DSN) as c:
        assert c.execute("SELECT che_do_cu, che_do_moi FROM goi_y_trang_chu_nhat_ky ORDER BY id DESC LIMIT 1").fetchone() == \
            ("tu_dong", "uu_tien")
        c.execute("DELETE FROM goi_y_trang_chu_nhat_ky WHERE id = (SELECT max(id) FROM goi_y_trang_chu_nhat_ky)")
    assert client.put("/analytics/home-suggestions", json={"gia_tri": "phong_cach:Khong_co", "che_do": "an"},
                      headers=sales).status_code == 404
    assert client.get("/analytics/home-suggestions").status_code == 401
    assert client.get("/analytics/home-suggestions", headers=as_role("architect")).status_code == 403
    assert client.put("/analytics/home-suggestions", json={"gia_tri": "phong_cach:Japandi", "che_do": "an"},
                      headers=as_role("visitor")).status_code == 403
