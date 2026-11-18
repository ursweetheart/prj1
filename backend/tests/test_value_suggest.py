"""Suggesting a new room type / style (change: review-tag-autocomplete 3.2). No network: vertex is monkeypatched."""

import pytest

from pipeline import taxonomy, value_suggest as vs


def _v(ten, syn=(), mo_ta=""):
    return {"ten": ten, "mo_ta": mo_ta, "syn": list(syn)}


TAX = {"phong_cach": {"ten": "Phong cách", "values": {
    "Japandi": _v("Japandi", [], "Nhật + Bắc Âu."), "Hien_dai": _v("Hiện đại", ["modern"]), "Khac": _v("Khác")}}}
SPACE = {"id": 1, "relative_path": "khong_co/anh.jpg", "caption": "Phòng khách gỗ sáng", "materials": ["gỗ sồi"],
         "palette": {"temperature": "warm", "brightness": "light"}, "hotspots": {"objects": [{"label_vi": "Sofa"}]}}


@pytest.fixture(autouse=True)
def tax(monkeypatch):
    monkeypatch.setattr(taxonomy, "_tax", lambda: TAX)


def test_key_ignores_case_accents_and_separators():
    assert vs.key("Mid-century") == vs.key("mid century") == vs.key("MID_CENTURY")


def test_spelling_catches_a_typo_without_ai():
    assert vs.spelling("phong_cach", "Japandy") == "Japandi"
    assert vs.spelling("phong_cach", "Mid-century") is None


def _gemini(monkeypatch, reply=None, error=None):
    seen = {}

    def fake(parts, **_):
        seen["parts"] = parts
        if error:
            raise error
        return reply, {}
    monkeypatch.setattr(vs.vertex, "available", lambda: True)
    monkeypatch.setattr(vs.vertex, "generate", fake)
    return seen


def test_ai_says_same_meaning(monkeypatch):
    seen = _gemini(monkeypatch, {"trung_voi": "Japandi", "ly_do": "Nhật Bắc Âu là Japandi", "mo_ta": "", "tu_dong_nghia": []})
    out = vs.ai_check(SPACE, "phong_cach", "Nhật Bắc Âu")
    assert out["trung_voi"] == "Japandi" and "Japandi" in out["ly_do"]
    prompt = seen["parts"][0]["text"]
    assert "Nhật Bắc Âu" in prompt and "- Japandi: Japandi. Nhật + Bắc Âu" in prompt and "Sofa" in prompt


def test_ai_invented_code_is_dropped_and_draft_kept(monkeypatch):
    _gemini(monkeypatch, {"trung_voi": "Mid_century", "ly_do": "x", "mo_ta": "Chân gỗ vát.",
                          "tu_dong_nghia": ["Mid Century ", "", "mcm"]})
    out = vs.ai_check(SPACE, "phong_cach", "Mid-century")
    assert out["trung_voi"] is None
    assert (out["mo_ta"], out["tu_dong_nghia"]) == ("Chân gỗ vát.", ["mid century", "mcm"])


def test_ai_failure_or_missing_key_gives_none(monkeypatch):
    _gemini(monkeypatch, error=RuntimeError("timeout"))
    assert vs.ai_check(SPACE, "phong_cach", "Mid-century") is None
    monkeypatch.setattr(vs.vertex, "available", lambda: False)
    assert vs.ai_check(SPACE, "phong_cach", "Mid-century") is None


def test_ai_explains_features_closest_value_and_photo_match(monkeypatch):
    seen = _gemini(monkeypatch, {"trung_voi": None, "ly_do": "phong cách riêng", "gan_nhat": "Hien_dai",
                                 "khac_biet": "chân gỗ vát, đường cong hữu cơ", "dac_trung": ["chân gỗ vát", " ", "tông cam nâu"],
                                 "anh_khop": False, "nhan_xet_anh": "Ảnh giống Indochine hơn", "mo_ta": "x", "tu_dong_nghia": []})
    out = vs.ai_check(SPACE, "phong_cach", "Mid-century")
    assert (out["gan_nhat"], out["anh_khop"]) == ("Hien_dai", False)
    assert out["dac_trung"] == ["chân gỗ vát", "tông cam nâu"] and "Indochine" in out["nhan_xet_anh"]
    assert "dac_trung" in seen["parts"][0]["text"] and "anh_khop" in seen["parts"][0]["text"]


def test_ai_odd_answers_are_cleaned(monkeypatch):
    _gemini(monkeypatch, {"gan_nhat": "Khong_co", "dac_trung": "not a list", "anh_khop": "yes"})
    out = vs.ai_check(SPACE, "phong_cach", "Mid-century")
    assert (out["gan_nhat"], out["dac_trung"], out["anh_khop"]) == (None, [], None)
