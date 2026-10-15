"""No database, no network."""
import pytest

from generate_kb import MARK, parse_reply, sample, to_chunk

GOOD = {"title": "Biệt thự Indochine gỗ tối", "match": "biệt thự phong cách Indochine gỗ tối gạch bông",
        "content": "Không gian dùng gỗ tối màu và gạch bông, nhiều mây tre.", "questions": ["Có dự án Indochine nào không?", " ", 5]}


def test_parse_reply_accepts_fenced_json():
    assert parse_reply('```json\n{"a": 1}\n```') == {"a": 1}


def test_chunk_is_marked_unreviewed_and_questions_are_cleaned():
    chunk, questions = to_chunk(GOOD, "Indochine")
    assert chunk["kind"] == "project" and chunk["content"].startswith(MARK)
    assert questions == ["Có dự án Indochine nào không?"]


@pytest.mark.parametrize("bad", ["Giá chỉ 500.000 đồng/m2.", "Bảo hành 24 tháng.", "Cam kết hoàn thành đúng hạn.",
                                 "Thiết kế miễn phí.", "Trọn gói 8 triệu mỗi m2."])
def test_claims_about_money_or_promises_are_refused(bad):
    with pytest.raises(ValueError):
        to_chunk({**GOOD, "content": bad}, "x")


def test_missing_field_is_refused():
    with pytest.raises(ValueError):
        to_chunk({**GOOD, "match": ""}, "x")


def test_sample_spreads_over_the_folder():
    assert sample(list(range(12)), 4) == [0, 3, 6, 9]
    assert sample([1, 2], 6) == [1, 2]
