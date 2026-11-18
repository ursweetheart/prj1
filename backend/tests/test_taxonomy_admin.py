"""Taxonomy admin (change taxonomy-admin): module rules, the merge fix, endpoints. Everything is throw-away:
dimensions 'tqa_*', values with codes 'tqa_*' / 'Tqa_*', spaces 'test_tqa_*/'; removed afterwards with their log rows."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import assistant, taxonomy, taxonomy_admin as ta
from pipeline.store import DSN


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def scratch():
    """Cleans every 'tqa' dimension, value, space and log row after the test."""
    yield
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE relative_path LIKE 'test_tqa_%%'")
        c.execute("DELETE FROM gia_tri_phan_loai WHERE lower(ma_dinh_danh) LIKE 'tqa%%' OR ma_dinh_danh = 'dia_trung_hai'")
        c.execute("DELETE FROM chieu_phan_loai WHERE ma_dinh_danh LIKE 'tqa%%'")
        c.execute("DELETE FROM nhat_ky_phan_loai WHERE doi_tuong LIKE '%%tqa%%' OR doi_tuong LIKE '%%dia_trung_hai%%'")
    taxonomy.reload()


def _dim_id(code):
    return _q("SELECT id FROM chieu_phan_loai WHERE ma_dinh_danh=%s", code)[0][0]


def _space(style=None, room="phong_khach", status="published", project="test_tqa_p1"):
    with psycopg.connect(DSN) as c:
        return c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status) VALUES (%s,%s,%s,%s) "
                         "RETURNING id", (f"{project}/{uuid.uuid4().hex[:8]}.jpg", room, style, status)).fetchone()[0]


def _tags(space_id):
    return {r[0] for r in _q("SELECT d.ma_dinh_danh || ':' || v.ma_dinh_danh FROM space_gia_tri sg JOIN gia_tri_phan_loai v "
                             "ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE sg.space_id=%s", space_id)}


def _logs(target_like):
    return _q("SELECT hanh_dong, truoc, sau FROM nhat_ky_phan_loai WHERE doi_tuong LIKE %s ORDER BY id", target_like)


# ── 1.1 module ─────────────────────────────────────────────────────────────────
def test_slug_and_synonyms():
    assert ta.slug("Địa Trung Hải") == "dia_trung_hai"
    assert ta.synonyms(["  Bắc Âu ", "bắc âu", "", "BẮC   ÂU", "gỗ"]) == ["bắc âu", "gỗ"]
    with pytest.raises(ta.Invalid):
        ta.synonyms(["x" * 61])
    with pytest.raises(ta.Invalid):
        ta.synonyms([f"s{i}" for i in range(31)])


def test_add_value_code_duplicate_and_log(scratch):
    pc = _dim_id("phong_cach")
    with psycopg.connect(DSN) as c:
        v = ta.add_value(c, None, pc, "Địa Trung Hải", "Trắng, xanh biển", ["  Mediterranean "])
    assert v["ma_dinh_danh"] == "dia_trung_hai" and v["tu_dong_nghia"] == ["mediterranean"]
    with psycopg.connect(DSN) as c, pytest.raises(ta.Conflict):
        ta.add_value(c, None, pc, "japandi")  # case-insensitive clash with Japandi
    assert [r[0] for r in _logs("phong_cach:dia_trung_hai")] == ["them_gia_tri"]


def test_edit_value_keeps_code_and_logs(scratch):
    pc = _dim_id("phong_cach")
    with psycopg.connect(DSN) as c:
        v = ta.add_value(c, None, pc, "Tqa Một")
        out = ta.edit_value(c, None, v["id"], ten="Tqa Hai", syn=["  Bắc Âu ", "bắc âu"])
        same = ta.edit_value(c, None, v["id"], ten="Tqa Hai")  # nothing changed: no log row
    assert out["ma_dinh_danh"] == "tqa_mot" and out["ten"] == "Tqa Hai" and out["tu_dong_nghia"] == ["bắc âu"]
    assert same["ten"] == "Tqa Hai"
    rows = _logs("phong_cach:tqa_mot")
    assert [r[0] for r in rows] == ["them_gia_tri", "sua_gia_tri"]
    assert rows[1][1]["ten"] == "Tqa Một" and rows[1][2]["ten"] == "Tqa Hai"


def test_dimension_add_rename_hide_and_move(scratch):
    with psycopg.connect(DSN) as c:
        a = ta.add_dimension(c, None, "Tqa Ánh sáng", nhieu=True, hien_thi=True)
        b = ta.add_dimension(c, None, "Tqa Bề mặt")
        with pytest.raises(ta.Conflict):
            ta.add_dimension(c, None, "tqa anh sang")
        assert a["ma_dinh_danh"] == "tqa_anh_sang" and a["cho_phep_nhieu_gia_tri"] and b["thu_tu"] == a["thu_tu"] + 1
        c.execute("UPDATE chieu_phan_loai SET thu_tu = %s WHERE id = %s", (a["thu_tu"], b["id"]))  # a tie
        ta.edit_dimension(c, None, b["id"], move="up")
        order = [r[0] for r in c.execute("SELECT id FROM chieu_phan_loai ORDER BY thu_tu, id").fetchall()]
        assert order.index(b["id"]) == order.index(a["id"]) - 1
        hidden = ta.edit_dimension(c, None, a["id"], ten="Tqa Đèn", hien_thi=False)
    assert hidden["ten"] == "Tqa Đèn" and hidden["hien_thi_cho_khach"] is False and hidden["ma_dinh_danh"] == "tqa_anh_sang"
    acts = [r[0] for r in _logs("tqa_anh_sang")]
    assert acts == ["them_chieu", "sua_chieu"]


def test_usage_counts(scratch):
    pc = _dim_id("phong_cach")
    with psycopg.connect(DSN) as c:
        v = ta.add_value(c, None, pc, "Tqa Dem")
    _space("tqa_dem", project="test_tqa_p1"), _space("tqa_dem", project="test_tqa_p1")
    _space("tqa_dem", status="draft", project="test_tqa_p2")
    with psycopg.connect(DSN) as c:
        assert ta.usage(c, v["id"]) == {"so_khong_gian": 3, "so_da_dang": 2, "so_du_an": 2}


# ── 1.2 merge ──────────────────────────────────────────────────────────────────
def test_merge_style_moves_the_space_column(scratch):
    pc = _dim_id("phong_cach")
    with psycopg.connect(DSN) as c:
        src, dst = ta.add_value(c, None, pc, "Tqa Src"), ta.add_value(c, None, pc, "Tqa Dst")
    s1, s2 = _space("tqa_src"), _space("tqa_src")
    assert "phong_cach:tqa_src" in _tags(s1)
    with psycopg.connect(DSN) as c:
        out = ta.merge(c, None, src["id"], dst["id"])
    assert out["so_khong_gian"] == 2 and out["cot_cap_nhat"] == 2
    assert {r[0] for r in _q("SELECT design_style FROM space WHERE id = ANY(%s)", [s1, s2])} == {"tqa_dst"}
    assert "phong_cach:tqa_dst" in _tags(s1) and "phong_cach:tqa_src" not in _tags(s1)
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE space SET caption = 'sửa chú thích', design_style = design_style WHERE id = %s", (s1,))
    assert "phong_cach:tqa_dst" in _tags(s1)  # survives a later edit (the old bug lost it)
    assert not _q("SELECT 1 FROM gia_tri_phan_loai WHERE id=%s", src["id"])
    assert [r[0] for r in _logs("phong_cach:tqa_src")][-1] == "gop_gia_tri"


def test_merge_refusals_change_nothing(scratch):
    pc, vl = _dim_id("phong_cach"), _dim_id("vat_lieu")
    with psycopg.connect(DSN) as c:
        a, b = ta.add_value(c, None, pc, "Tqa A"), ta.add_value(c, None, vl, "Tqa B")
    s = _space("tqa_a")
    tm = {r[1]: r[0] for r in _q("SELECT v.id, v.ma_dinh_danh FROM gia_tri_phan_loai v JOIN chieu_phan_loai d "
                                 "ON d.id=v.chieu_id WHERE d.ma_dinh_danh='tong_mau'")}
    for src, dst in [(a["id"], b["id"]), (tm["light"], tm["dark"]), (a["id"], a["id"])]:
        with psycopg.connect(DSN) as c, pytest.raises(ta.Invalid):
            ta.merge(c, None, src, dst)
    assert "phong_cach:tqa_a" in _tags(s) and _q("SELECT design_style FROM space WHERE id=%s", s)[0][0] == "tqa_a"
    assert len(_q("SELECT 1 FROM gia_tri_phan_loai WHERE id = ANY(%s)", [tm["light"], tm["dark"]])) == 2


# ── 1.3 endpoints ──────────────────────────────────────────────────────────────
def test_endpoints_roles_and_public_effect(scratch, as_role):
    boss, sales = as_role("lead_architect"), as_role("sales")
    assert client.get("/taxonomy/admin").status_code == 401
    assert client.get("/taxonomy/admin", headers=sales).status_code == 403
    assert client.post("/taxonomy", json={"ten": "Tqa X"}, headers=sales).status_code == 403
    tree = client.get("/taxonomy/admin", headers=boss).json()
    assert tree["chieu"] and all("so_khong_gian" in v for d in tree["chieu"] for v in d["gia_tri"])
    assert next(d for d in tree["chieu"] if d["ma_dinh_danh"] == "tong_mau")["co_the_gop"] is False

    dim = client.post("/taxonomy", json={"ten": "Tqa Ánh sáng", "cho_phep_nhieu_gia_tri": True}, headers=boss)
    assert dim.status_code == 201 and dim.json()["ma_dinh_danh"] == "tqa_anh_sang"
    did = dim.json()["id"]
    val = client.post(f"/taxonomy/{did}/values", json={"ten": "Tqa Ấm"}, headers=boss)
    assert val.status_code == 201 and val.json()["ma_dinh_danh"] == "tqa_am"
    assert client.post(f"/taxonomy/{did}/values", json={"ten": "TQA ấm"}, headers=boss).status_code == 409
    public = {d["ma_dinh_danh"]: d for d in client.get("/taxonomy").json()}
    assert "tqa_am" in {v["ma_dinh_danh"] for v in public["tqa_anh_sang"]["values"]}
    assert client.patch(f"/taxonomy/{did}", json={"hien_thi_cho_khach": False}, headers=boss).status_code == 200
    assert {d["ma_dinh_danh"]: d for d in client.get("/taxonomy").json()}["tqa_anh_sang"]["hien_thi_cho_khach"] is False
    assert client.patch(f"/taxonomy/{did}", json={"move": "sideways"}, headers=boss).status_code == 422
    order = [d["ma_dinh_danh"] for d in client.get("/taxonomy").json()]
    up = client.patch(f"/taxonomy/{did}", json={"move": "up"}, headers=boss)
    assert up.status_code == 200
    after = [d["ma_dinh_danh"] for d in client.get("/taxonomy").json()]
    at = order.index("tqa_anh_sang")
    assert after.index("tqa_anh_sang") == at - 1 and after[at] == order[at - 1]
    assert client.patch(f"/taxonomy/{did}", json={"move": "down"}, headers=boss).status_code == 200
    assert client.patch("/taxonomy/999999", json={"ten": "x"}, headers=boss).status_code == 404
    log = client.get("/taxonomy/admin", headers=boss).json()["gan_day"]
    assert log[0]["hanh_dong"] == "sua_chieu" and log[0]["email"].endswith("@example.com")


def test_new_synonym_parses_at_once(scratch, as_role):
    boss = as_role("lead_architect")
    sc = next(v for d in client.get("/taxonomy").json() if d["ma_dinh_danh"] == "phong_cach"
              for v in d["values"] if v["ma_dinh_danh"] == "Scandinavian")
    before = list(sc["tu_dong_nghia"])
    try:
        assert assistant.parse_request("phòng khách kiểu bac au")["design_style"] is None
        r = client.patch(f"/taxonomy/values/{sc['id']}", json={"tu_dong_nghia": before + ["  Bắc Âu ", "bắc âu"]}, headers=boss)
        assert r.status_code == 200 and r.json()["tu_dong_nghia"] == before + ["bắc âu"] and r.json()["ma_dinh_danh"] == "Scandinavian"
        assert assistant.parse_request("phòng khách kiểu bac au")["design_style"] == "Scandinavian"
    finally:
        client.patch(f"/taxonomy/values/{sc['id']}", json={"tu_dong_nghia": before}, headers=boss)
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM nhat_ky_phan_loai WHERE doi_tuong = 'phong_cach:Scandinavian'")


def test_merge_endpoint_cross_dimension_422(scratch, as_role):
    boss = as_role("lead_architect")
    pc, vl = _dim_id("phong_cach"), _dim_id("vat_lieu")
    a = client.post(f"/taxonomy/{pc}/values", json={"ten": "Tqa A"}, headers=boss).json()
    b = client.post(f"/taxonomy/{vl}/values", json={"ten": "Tqa B"}, headers=boss).json()
    r = client.post(f"/taxonomy/values/{a['id']}/merge", json={"target_id": b["id"]}, headers=boss)
    assert r.status_code == 422 and "same dimension" in r.json()["detail"]


# ── classifier-reads-taxonomy 3.1: room type / style are checked against the stored values ──
def test_staff_can_set_a_style_added_by_hand(scratch, as_role):
    lead = as_role("lead_architect")
    v = client.post(f"/taxonomy/{_dim_id('phong_cach')}/values", json={"ten": "Tqa Mid century"}, headers=lead).json()
    sid = _space(style="Hien_dai", status="draft")
    r = client.patch(f"/spaces/{sid}", json={"design_style": v["ma_dinh_danh"]}, headers=as_role("architect"))
    assert r.status_code == 200, r.text
    assert f"phong_cach:{v['ma_dinh_danh']}" in _tags(sid)


def test_unknown_style_or_room_is_422_and_changes_nothing(scratch, as_role):
    h = as_role("architect")
    sid = _space(style="Hien_dai", status="draft")
    r = client.patch(f"/spaces/{sid}", json={"design_style": "Tqa_khong_co"}, headers=h)
    assert r.status_code == 422 and "Hien_dai" in r.text
    assert client.patch(f"/spaces/{sid}", json={"space_type": "tqa_garage"}, headers=h).status_code == 422
    assert client.get("/search", params={"q": "x", "space_type": "tqa_garage"}).status_code == 422
    assert _q("SELECT design_style, space_type FROM space WHERE id=%s", sid)[0] == ("Hien_dai", "phong_khach")
