"""No database needed."""
from eval_labels import compare, folder_check


def test_unedited_counts_as_accepted_and_edits_as_misses():
    rows = [("a/1.jpg", "phong_khach", "Luxury", None, None),                    # accepted as is
            ("a/2.jpg", "phong_khach", "Hien_dai", None, "Luxury"),              # style fixed by a human
            ("a/3.jpg", "bep_va_an", "Luxury", "phong_khach", None)]             # type fixed by a human
    score, misses = compare(rows)
    assert score == {"space_type": (2, 3), "design_style": (2, 3)}
    assert misses == [("a/2.jpg", "design_style", "Luxury", "Hien_dai"), ("a/3.jpg", "space_type", "phong_khach", "bep_va_an")]


def test_folder_check_ignores_unknown_folders():
    assert folder_check([("luxury/1.jpg", "Luxury"), ("luxury/2.jpg", "Hien_dai"), ("hanjadin/1.jpg", "Luxury")]) == (1, 2)
