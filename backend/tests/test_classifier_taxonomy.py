"""The AI tagger reads its room types and styles from the taxonomy (change: classifier-reads-taxonomy). No DB, no AI."""

import copy
import json
from pathlib import Path

import pytest

from pipeline import taxonomy
from pipeline.color_extractor import ColorAnalysisResult
from pipeline.multimodal_classifier import MultimodalClassifier, system_prompt
from pipeline.schemas import FurnitureDetectionResult


def _v(ten, syn=(), mo_ta=""):
    return {"ten": ten, "mo_ta": mo_ta, "syn": list(syn)}


TAX = {
    "khong_gian": {"ten": "Không gian", "values": {
        "phong_khach": _v("Phòng khách", ["phong khach"]), "phong_tam": _v("Phòng tắm"), "khac": _v("Khác")}},
    "phong_cach": {"ten": "Phong cách", "values": {
        "Hien_dai": _v("Hiện đại", ["hien dai", "modern"], "Tinh gọn, công năng."),
        "Wabi_sabi": _v("Wabi-sabi", ["wabi sabi"]),
        "Mid_century": _v("Mid-century", [], "Chân gỗ vát, đường cong hữu cơ, thập niên 50-60."),
        "Khac": _v("Khác")}},
}


@pytest.fixture(autouse=True)
def tax(monkeypatch):
    t = copy.deepcopy(TAX)  # a test may edit its copy
    monkeypatch.setattr(taxonomy, "_tax", lambda: t)
    return t


@pytest.mark.parametrize("answer,code", [
    ("Hien_dai", "Hien_dai"), ("hien_dai", "Hien_dai"), ("Hiện đại", "Hien_dai"), ("hien dai", "Hien_dai"),
    ("Modern", "Hien_dai"), ("wabi-sabi", "Wabi_sabi"), ("WabiSabi", "Wabi_sabi"), ("Mid-century", "Mid_century"),
])
def test_resolve_matches_code_name_and_synonym(answer, code):
    assert taxonomy.resolve("phong_cach", answer) == code


@pytest.mark.parametrize("answer", ["Art deco", "", None, "   "])
def test_resolve_unknown_is_none(answer):
    assert taxonomy.resolve("phong_cach", answer) is None


def test_prompt_lists_stored_values_with_descriptions(tax):
    p = system_prompt()
    assert "- Mid_century: Mid-century. Chân gỗ vát" in p
    assert "- phong_tam: Phòng tắm" in p
    del tax["phong_cach"]["values"]["Mid_century"]
    assert "Mid_century" not in system_prompt()


def _parse(**answer):
    base = {"space_type": "phong_khach", "design_style": "Hien_dai", "design_style_confidence": 0.9,
            "style_rationale": "x", "materials": ["gỗ"], "seo_metadata": {"caption": "c", "alt_text": "a"}}
    return MultimodalClassifier()._clean_and_parse_json(json.dumps({**base, **answer}))


def test_new_value_is_kept():
    r = _parse(design_style="Mid-century")
    assert (r.design_style, r.design_style_confidence) == ("Mid_century", 0.9)


def test_display_name_or_synonym_becomes_the_code():
    assert _parse(design_style="Hiện đại").design_style == "Hien_dai"
    assert _parse(design_style="modern").design_style == "Hien_dai"


def test_unknown_style_is_other_with_zero_confidence():
    r = _parse(design_style="Art deco", design_style_confidence=0.97)
    assert (r.design_style, r.design_style_confidence) == ("Khac", 0.0)


def test_unknown_room_is_other_not_living_room():
    r = _parse(space_type="garage")
    assert (r.space_type, r.space_type_label) == ("khac", "Khác")


def test_room_label_comes_from_the_taxonomy():
    assert _parse(space_type="Phòng tắm").space_type_label == "Phòng tắm"


def _heuristic(folder):
    color = ColorAnalysisResult(palette=[], dominant_hex="#ffffff", brightness="light", temperature="warm",
                                weighted_luminance=70.0)
    furniture = FurnitureDetectionResult(objects=[], counts_by_category={"sofa": 1}, inference_time_ms=0.0)
    return MultimodalClassifier()._heuristic_classify(Path(f"{folder}/a.jpg"), color, furniture, folder)


def test_offline_fallback_keeps_a_stored_code():
    assert _heuristic("modern").design_style == "Hien_dai"


def test_offline_fallback_with_merged_away_code_is_other():
    r = _heuristic("hanjadin")  # the folder rule says Japandi, which this taxonomy no longer has
    assert (r.design_style, r.design_style_confidence) == ("Khac", 0.0)


# ── hotspot-accuracy 1.2: the classifier also names and points at items ──────────────────────────────────────────
def test_items_are_parsed_and_bad_ones_dropped():
    r = _parse(items=[
        {"ten": "Sofa vải xám", "loai": "sofa", "diem": [640, 420]},
        {"ten": "Đèn chùm", "loai": "den", "diem": [80, 500]},
        {"ten": "Bình hoa", "loai": "binh", "diem": [500, 500]},      # unknown category
        {"ten": "", "loai": "ghe", "diem": [500, 500]},              # no name
        {"ten": "Thảm", "loai": "thao", "diem": [1200, 500]},        # off the photo
        {"ten": "Tủ", "loai": "tu", "diem": [500]},                  # not a point
        "rác",
    ])
    assert [(i.ten, i.loai, i.x, i.y) for i in r.items] == [("Sofa vải xám", "sofa", 0.42, 0.64), ("Đèn chùm", "den", 0.5, 0.08)]


def test_items_missing_or_too_many():
    assert _parse().items == []
    many = [{"ten": f"Ghế {i}", "loai": "ghe", "diem": [500, 100 + i]} for i in range(12)]
    assert len(_parse(items=many).items) == 8


def test_prompt_asks_for_items_with_the_category_list():
    p = system_prompt()
    assert "MÓN NỘI THẤT CHÍNH" in p and "sofa, ghe, giuong" in p and "{loai}" not in p


def test_offline_fallback_has_no_items():
    assert _heuristic("modern").items == []
