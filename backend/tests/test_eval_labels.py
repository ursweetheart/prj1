"""No database needed."""
from eval_labels import by_band, compare, folder_check


def test_unedited_counts_as_accepted_and_edits_as_misses():
    rows = [("a/1.jpg", "phong_khach", "Luxury", None, None),                    # accepted as is
            ("a/2.jpg", "phong_khach", "Hien_dai", None, "Luxury"),              # style fixed by a human
            ("a/3.jpg", "bep_va_an", "Luxury", "phong_khach", None)]             # type fixed by a human
    score, misses = compare(rows)
    assert score == {"space_type": (2, 3), "design_style": (2, 3)}
    assert misses == [("a/2.jpg", "design_style", "Luxury", "Hien_dai"), ("a/3.jpg", "space_type", "phong_khach", "bep_va_an")]


def test_folder_check_ignores_unknown_folders():
    assert folder_check([("luxury/1.jpg", "Luxury"), ("luxury/2.jpg", "Hien_dai"), ("hanjadin/1.jpg", "Luxury")]) == (1, 2)


def test_accuracy_per_confidence_band():
    rows = [("a/1.jpg", "phong_khach", "Luxury", "phong_khach", "Luxury", 0.95, 0.4),      # style right at 0.4
            ("a/2.jpg", "phong_khach", "Hien_dai", "phong_khach", "Luxury", 0.95, 0.45),   # style wrong at 0.45
            ("a/3.jpg", "bep_va_an", "Luxury", "phong_khach", "Luxury", 0.6, None)]        # no style confidence
    b = by_band(rows)
    assert b["design_style"][0] == ("dưới 0.5", 1, 2)
    assert b["space_type"] == [("dưới 0.5", 0, 0), ("0.5–0.7", 0, 1), ("0.7–0.9", 0, 0), ("0.9 trở lên", 2, 2)]
