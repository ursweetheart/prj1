"""Discovery scoring and staging (change: discover-taxonomy-dimensions). The first block needs neither DB nor API;
the run() tests need the DB and replace Gemini with canned replies."""

import psycopg
import pytest

from pipeline import discovery
from pipeline.discovery import MULTI_SOURCE_BOOST, PENALTY, WEIGHTS, evidence, merge, parse_and_score, score
from pipeline.store import DSN


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
    assert by["Phong cách lại"] <= WEIGHTS["coverage"]  # no distinct credit


def test_example_ids_dict_shape_counts_unique_spaces():
    """Gemini sometimes returns vi_du_space_ids as {value: [ids]}; coverage must union them."""
    reply = {"candidates": [{"ten": "Liên thông", "trung_voi_chieu_hien_co": False, "do_tin_cay": 1.0,
                             "vi_du_space_ids": {"a": [1, 2, 3], "b": [3, 4]}}]}
    [c] = parse_and_score(reply, n=4)
    assert c["coverage"] == 1.0 and c["score"] == WEIGHTS["coverage"] + WEIGHTS["distinct"]


def test_second_source_raises_the_score():
    c = {"ten": "x", "vi_du_space_ids": [1, 2], "do_tin_cay": 0.8, "cau_hoi_lien_quan": [7, 8, 9]}
    alone = evidence(c, 10, {}, gap_ids=set())
    with_chat = evidence(c, 10, {}, gap_ids={7, 8, 9})
    assert alone["nguon"] == ["image"] and with_chat["nguon"] == ["image", "chat"]
    assert score(with_chat) == pytest.approx(score(alone) + WEIGHTS["demand"] + MULTI_SOURCE_BOOST, abs=1e-3)


def test_one_question_is_demand_but_not_yet_a_source():
    ev = evidence({"ten": "x", "cau_hoi_lien_quan": [7]}, 10, {}, gap_ids={7})
    assert ev["nguon"] == ["image"] and ev["demand"] > 0


def test_behaviour_lift_counts_as_a_source():
    ev = evidence({"ten": "x", "vi_du_space_ids": [1]}, 10, {"do_nang_xem": 2.0})
    assert ev["nguon"] == ["image", "behavior"] and ev["demand"] == 1.0


def test_not_orthogonal_or_failed_check_is_penalised():
    base = {"coverage": 1.0, "distinct": 1.0, "demand": 0.0, "nguon": ["image"]}
    full = score(base)
    assert score({**base, "truc_giao": False}) == pytest.approx(full * PENALTY)
    assert score({**base, "kiem_tra": False}) == pytest.approx(full * PENALTY)


def test_merge_keeps_strongest_evidence_and_unions_sources():
    m = merge({"coverage": 0.5, "demand": 0.0, "nguon": ["image"], "vi_du_space_ids": [1]},
              {"coverage": 0.2, "demand": 0.7, "nguon": ["image", "chat"], "vi_du_space_ids": [2]})
    assert m["coverage"] == 0.5 and m["demand"] == 0.7
    assert m["nguon"] == ["chat", "image"] and m["vi_du_space_ids"] == [1, 2]


# ── run() against the DB with Gemini replaced ────────────────────────────────

def _fake_gemini(monkeypatch, proposals, verdicts):
    calls = []

    def generate(parts, **kw):
        text = parts[0]["text"]
        calls.append(text)
        if "Các chiều MỚI được đề xuất" in text:
            return {"ket_qua": verdicts}, None
        return {"candidates": proposals}, None

    monkeypatch.setattr(discovery.vertex, "generate", generate)
    return calls


@pytest.fixture
def clean_candidates():
    def wipe():
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM ung_vien_phan_loai WHERE ten_de_xuat LIKE %s", (discovery.MARK + "TEST %",))
    wipe()
    yield
    wipe()


def _rows():
    with psycopg.connect(DSN) as c:
        return dict(c.execute("SELECT ten_de_xuat, trang_thai FROM ung_vien_phan_loai WHERE ten_de_xuat LIKE %s",
                              (discovery.MARK + "TEST %",)).fetchall())


def _ids(n):
    with psycopg.connect(DSN) as c:  # spaces of several types and styles, so the proposal is orthogonal
        return [r[0] for r in c.execute("SELECT DISTINCT ON (space_type) id FROM space ORDER BY space_type, id LIMIT %s", (n,))]


def test_run_promotes_strong_holds_weak_and_never_creates_a_dimension(monkeypatch, clean_candidates):
    ids = _ids(4)
    calls = _fake_gemini(monkeypatch, [
        {"ten": "TEST Mật độ cây xanh", "gia_tri": ["Nhiều", "Ít"], "vi_du_space_ids": ids, "do_tin_cay": 1.0},
        {"ten": "TEST Yếu", "gia_tri": ["a", "b"], "vi_du_space_ids": ids[:1], "do_tin_cay": 0.2},
    ], [{"ten": "TEST Mật độ cây xanh", "trung_lap": False, "dat_ten_duoc": True, "ly_do": "mới"}])
    monkeypatch.setattr(discovery, "THRESHOLD", 0.3)
    with psycopg.connect(DSN) as c:
        dims_before = c.execute("SELECT count(*) FROM chieu_phan_loai").fetchone()[0]
    discovery.run(limit=8)
    assert _rows() == {discovery.MARK + "TEST Mật độ cây xanh": "cho_duyet", discovery.MARK + "TEST Yếu": "cho_bang_chung"}
    assert len(calls) == 2  # propose + check, nothing more
    with psycopg.connect(DSN) as c:  # 4.2: discovery alone never creates a dimension
        assert c.execute("SELECT count(*) FROM chieu_phan_loai").fetchone()[0] == dims_before


def test_failed_check_is_held_and_a_rerun_merges_into_the_same_row(monkeypatch, clean_candidates):
    ids = _ids(4)
    prop = [{"ten": "TEST Liên thông", "gia_tri": ["Mở", "Kín"], "vi_du_space_ids": ids, "do_tin_cay": 1.0}]
    _fake_gemini(monkeypatch, prop, [{"ten": "TEST Liên thông", "trung_lap": True, "dat_ten_duoc": True}])
    monkeypatch.setattr(discovery, "THRESHOLD", 0.3)
    discovery.run(limit=8)
    assert _rows() == {discovery.MARK + "TEST Liên thông": "cho_bang_chung"}
    _fake_gemini(monkeypatch, prop, [{"ten": "TEST Liên thông", "trung_lap": False, "dat_ten_duoc": True}])
    discovery.run(limit=8)
    assert _rows() == {discovery.MARK + "TEST Liên thông": "cho_duyet"}  # same row, re-checked, now promoted


def test_rejected_proposal_does_not_come_back(monkeypatch, clean_candidates):
    with psycopg.connect(DSN) as c:
        c.execute("INSERT INTO ung_vien_phan_loai (loai, ten_de_xuat, trang_thai) VALUES ('chieu', %s, 'tu_choi')",
                  (discovery.MARK + "TEST Bị từ chối",))
    _fake_gemini(monkeypatch, [{"ten": "TEST bị TỪ CHỐI", "gia_tri": ["a", "b"], "vi_du_space_ids": _ids(2), "do_tin_cay": 1}], [])
    found = discovery.run(limit=8)
    assert not any(discovery._key(c["ten"]) == discovery._key("TEST Bị từ chối") for c in found)
