"""Ranking example projects (change: assistant-project-results 1.1). No DB, no AI: the taxonomy is monkeypatched."""

import pytest

from pipeline import project_results as pr, taxonomy

TAX = {
    "phong_cach": {"ten": "Phong cách", "values": {"Japandi": {"ten": "Japandi", "mo_ta": "", "syn": []}}},
    "khong_gian": {"ten": "Không gian", "values": {"phong_khach": {"ten": "Phòng khách", "mo_ta": "", "syn": []},
                                                   "phong_ngu_master": {"ten": "Phòng ngủ master", "mo_ta": "", "syn": []}}},
    "loai_cong_trinh": {"ten": "Loại công trình", "values": {"chung_cu": {"ten": "Chung cư", "mo_ta": "", "syn": []},
                                                             "biet_thu": {"ten": "Biệt thự", "mo_ta": "", "syn": []}}},
}


@pytest.fixture(autouse=True)
def tax(monkeypatch):
    monkeypatch.setattr(taxonomy, "_tax", lambda: TAX)


def ph(i, folder, room, style, sim, loai=("chung_cu",)):
    return {"id": i, "relative_path": f"{folder}/{i}.jpg", "space_type": room, "design_style": style,
            "loai_cong_trinh": list(loai), "sim": sim}


REQ = {"design_style": "Japandi", "space_type": "phong_khach", "project_type": "chung_cu"}


def test_photos_are_grouped_by_project():
    photos = [ph(1, "a", "phong_khach", "Japandi", .9), ph(2, "b", "phong_khach", "Japandi", .89),
              ph(3, "a", "phong_khach", "Japandi", .88), ph(4, "a", "bep_va_an", "Japandi", .8), ph(5, "b", "phong_tam", "Japandi", .7)]
    out = pr.rank(photos, REQ)
    assert [p["folder"] for p in out] == ["a", "b"] and [p["so_anh_khop"] for p in out] == [3, 2]


def test_more_matched_constraints_beat_higher_similarity():
    photos = [ph(1, "B", "phong_ngu_master", "Japandi", .95, loai=("biet_thu",)),
              ph(2, "A", "phong_khach", "Japandi", .80), ph(3, "A", "phong_ngu_master", "Japandi", .78)]
    out = pr.rank(photos, REQ)
    assert [p["folder"] for p in out] == ["A", "B"]
    assert [m["ten"] for m in out[0]["khop"]] == ["Japandi", "Phòng khách", "Chung cư"]
    assert [m["ten"] for m in out[1]["khop"]] == ["Japandi"]


def test_no_constraints_ranks_by_similarity_and_shows_no_match_line():
    photos = [ph(1, "x", "phong_khach", "Japandi", .7), ph(2, "y", "phong_khach", "Japandi", .9)]
    out = pr.rank(photos, {})
    assert [p["folder"] for p in out] == ["y", "x"] and all(p["khop"] == [] for p in out)


def test_best_matching_photos_first_and_capped():
    photos = [ph(1, "a", "bep_va_an", "Japandi", .95), ph(2, "a", "phong_khach", "Japandi", .7),
              ph(3, "a", "phong_khach", "Japandi", .8)]
    out = pr.rank(photos, REQ)
    assert [p["id"] for p in out[0]["anh"]] == [3, 2]  # both match the room; the one that doesn't comes last


def test_at_most_three_projects():
    photos = [ph(i, f"p{i}", "phong_khach", "Japandi", .9 - i / 100) for i in range(6)]
    assert len(pr.rank(photos, REQ)) == 3


def test_keep_order_follows_first_use():
    photos = [ph(1, "z", "phong_tam", "Khac", .5), ph(2, "a", "phong_khach", "Japandi", .9), ph(3, "z", "phong_tam", "Khac", .4)]
    out = pr.rank(photos, REQ, keep_order=True)
    assert [p["folder"] for p in out] == ["z", "a"] and [p["id"] for p in out[0]["anh"]] == [1, 3]
