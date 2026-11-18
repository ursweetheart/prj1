"""Guards for the taxonomy seed (changes: discover-taxonomy-dimensions, classifier-reads-taxonomy)."""

import psycopg
from psycopg.types.json import Jsonb

from pipeline.store import DSN
from seed_taxonomy import check, load, seed

ROOMS = {"phong_khach", "phong_ngu_master", "phong_ngu_phu", "bep_va_an", "phong_lam_viec",
         "sanh_thong_tang", "ban_cong", "phong_tam", "lounge_thuong_mai", "khac"}
STYLES = {"Indochine", "Japandi", "Wabi_sabi", "Hien_dai", "Tan_co_dien", "Luxury", "Toi_gian", "Scandinavian", "Khac"}


def test_seed_is_internally_consistent():
    assert check(load()) == []


def test_seed_keeps_the_codes_spaces_already_hold():
    """space.space_type / design_style rows were written with these codes; the seed must keep every one."""
    by_dim: dict[str, set] = {}
    for v in load()["gia_tri"]:
        by_dim.setdefault(v["chieu"], set()).add(v["ma_dinh_danh"])
    assert ROOMS <= by_dim["khong_gian"]
    assert STYLES <= by_dim["phong_cach"]


def test_every_style_has_a_description():
    assert all(v.get("mo_ta") for v in load()["gia_tri"] if v["chieu"] == "phong_cach")


def test_reseeding_keeps_staff_edits_and_fills_gaps():
    q = ("SELECT v.ten, v.tu_dong_nghia, v.mo_ta FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id "
         "WHERE d.ma_dinh_danh = 'phong_cach' AND v.ma_dinh_danh = 'Luxury'")
    with psycopg.connect(DSN) as c:
        before = c.execute(q).fetchone()
    try:
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE gia_tri_phan_loai v SET ten = 'Sang trọng', tu_dong_nghia = '[\"xa xi\"]', mo_ta = NULL "
                      "FROM chieu_phan_loai d WHERE d.id = v.chieu_id AND d.ma_dinh_danh = 'phong_cach' "
                      "AND v.ma_dinh_danh = 'Luxury'")
        seed()
        with psycopg.connect(DSN) as c:
            ten, syn, mo_ta = c.execute(q).fetchone()
        assert ten == "Sang trọng"          # rename kept
        assert syn == ["xa xi"]             # staff synonym kept (the seed has none for Luxury)
        assert mo_ta and "cẩm thạch" in mo_ta  # empty description filled from the seed
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE gia_tri_phan_loai v SET ten = %s, tu_dong_nghia = %s, mo_ta = %s "
                      "FROM chieu_phan_loai d WHERE d.id = v.chieu_id AND d.ma_dinh_danh = 'phong_cach' "
                      "AND v.ma_dinh_danh = 'Luxury'", (before[0], Jsonb(before[1]), before[2]))
