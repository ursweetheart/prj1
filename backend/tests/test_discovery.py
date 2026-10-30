"""No-DB / no-API guards for discovery scoring (change: discover-taxonomy-dimensions)."""

from pipeline.discovery import parse_and_score


def _reply():
    return {"candidates": [
        {"ten": "Mật độ cây xanh", "gia_tri": ["Nhiều", "Vừa", "Không"],
         "vi_du_space_ids": [1, 2, 3, 4], "trung_voi_chieu_hien_co": False, "do_tin_cay": 0.9},
        {"ten": "Phong cách lại", "gia_tri": ["x"],
         "vi_du_space_ids": [1], "trung_voi_chieu_hien_co": True, "do_tin_cay": 0.9},
    ]}


def test_distinct_well_covered_beats_non_distinct():
    scored = parse_and_score(_reply(), n=4)
    assert scored[0]["ten"] == "Mật độ cây xanh"  # sorted best-first
    by = {c["ten"]: c["score"] for c in scored}
    assert by["Mật độ cây xanh"] > by["Phong cách lại"]


def test_non_distinct_scores_zero_distinct_component():
    scored = parse_and_score(_reply(), n=4)
    non_distinct = next(c for c in scored if c["trung_voi_chieu_hien_co"])
    # distinct term is 0, so score is at most the coverage weight (0.6)
    assert non_distinct["score"] <= 0.6


def test_example_ids_dict_shape_counts_unique_spaces():
    """Gemini sometimes returns vi_du_space_ids as {value: [ids]}; coverage must union them."""
    reply = {"candidates": [
        {"ten": "Liên thông", "trung_voi_chieu_hien_co": False, "do_tin_cay": 1.0,
         "vi_du_space_ids": {"a": [1, 2, 3], "b": [3, 4]}},  # 4 unique spaces of 4 -> full coverage
    ]}
    [c] = parse_and_score(reply, n=4)
    assert c["score"] == 1.0  # 0.6*1.0 coverage + 0.4*1.0 distinct
