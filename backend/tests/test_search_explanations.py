"""search-explanations 1.1-1.3: reasons on similar and description results, the interior check and traits of an
uploaded photo, constraints from a description and the weak-match hint."""
import io
from pathlib import Path

import psycopg
from PIL import Image, ImageDraw

from conftest import client
from pipeline import explain
from pipeline.store import DSN


def _q(sql, *a):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, a).fetchall()


def test_similar_spaces_carry_shared_label_reasons():
    sid = _q("SELECT id FROM space WHERE review_status='published' ORDER BY id LIMIT 1")[0][0]
    hits = client.get(f"/spaces/{sid}/similar").json()
    assert hits and all(isinstance(h["ly_do"], list) and len(h["ly_do"]) <= 3 for h in hits)
    with psycopg.connect(DSN) as c:
        src = {(d, v) for d, _, v, _ in explain.labels(c, [sid])[sid]}
        for h in hits:
            mine = explain.labels(c, [h["id"]])[h["id"]]
            shared = {f"Cùng {explain.phrase(d, dn, vn)}" for d, dn, v, vn in mine if (d, v) in src}
            assert set(h["ly_do"]) <= shared and all("Khác" not in r for r in h["ly_do"])


def test_shared_reasons_sentence_and_nothing_shared():
    with psycopg.connect(DSN) as c:
        a, b = (r[0] for r in c.execute("SELECT id FROM space WHERE review_status='published' AND design_style='Indochine' "
                                        "ORDER BY id LIMIT 2"))
        why = explain.shared_reasons(c, a, [b])[b]
        assert "Cùng phong cách Indochine" in why
        assert explain.shared_reasons(c, a, [0])[0] == []


def test_description_constraints_filter_and_are_listed():
    r = client.get("/search", params={"q": "phòng ngủ indochine gỗ sẫm", "k": 12}).json()
    assert {(c["chieu"], c["ma"]) for c in r["rang_buoc"]} == {("khong_gian", "phong_ngu_master"), ("phong_cach", "Indochine")}
    assert r["ket_qua"] and all(h["space_type"] == "phong_ngu_master" and h["design_style"] == "Indochine" for h in r["ket_qua"])
    assert all("Indochine" in h["ly_do"] for h in r["ket_qua"]) and r["goi_y"] is None


def test_explicit_space_type_wins_over_the_sentence():
    r = client.get("/search", params={"q": "phòng ngủ ấm áp", "space_type": "phong_khach"}).json()
    assert all(c["chieu"] != "khong_gian" for c in r["rang_buoc"]) and all(h["space_type"] == "phong_khach" for h in r["ket_qua"])


def test_synonym_and_accents_are_matched():
    found, rest = explain.parse_query("PHONG NGU phong cach wabi sabi")
    assert {f["ma"] for f in found} == {"phong_ngu_master", "Wabi_sabi"} and rest == "phong cach"


def test_reasons_name_a_material_the_description_mentions():
    with psycopg.connect(DSN) as c:
        sid = c.execute("SELECT sg.space_id FROM space_gia_tri sg JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id "
                        "WHERE g.ten ILIKE 'gỗ%%' LIMIT 1").fetchone()[0]
        name = c.execute("SELECT g.ten FROM space_gia_tri sg JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id "
                         "WHERE sg.space_id=%s AND g.ten ILIKE 'gỗ%%'", (sid,)).fetchone()[0]
        assert name in explain.text_reasons(c, "phòng có nhiều gỗ", [], [sid])[sid]


def test_vague_description_gets_the_hint_and_still_results():
    r = client.get("/search", params={"q": "xe hơi màu đỏ"}).json()
    assert r["goi_y"] and r["ket_qua"]


def _png(draw):
    im = Image.new("RGB", (640, 480), "white")
    draw(ImageDraw.Draw(im))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def test_a_non_interior_is_refused_politely():
    data = _png(lambda d: [d.text((20, 20 + i * 18), "Hợp đồng thiết kế số %d" % i, fill="black") for i in range(20)])
    r = client.post("/search/image", files={"file": ("doc.png", data)}).json()
    assert r == {"noi_that": False, "thong_bao": r["thong_bao"], "dac_diem": {}, "ket_qua": []} and "không phải ảnh nội thất" in r["thong_bao"]


def test_an_interior_gets_traits_and_results():
    path = _q("SELECT relative_path FROM space WHERE review_status='published' AND design_style='Indochine' LIMIT 1")[0][0]
    r = client.post("/search/image", files={"file": ("a.jpg", Path("image_d3", path).read_bytes())}).json()
    assert r["noi_that"] is True and r["ket_qua"]
    assert r["dac_diem"].get("phong_cach", {}).get("ma") == "Indochine" and r["dac_diem"]["phong_cach"]["do_tin_cay"] >= 0.4
    assert any(x.startswith("Cùng phong cách") for h in r["ket_qua"] for x in h["ly_do"])
