"""No-DB guards for the taxonomy seed (change: discover-taxonomy-dimensions)."""

from seed_taxonomy import check, load


def test_seed_is_internally_consistent():
    assert check(load()) == []


def test_seed_matches_current_literals():
    """The seeded value ids must equal today's Literal enums, so the later
    data cutover maps space.space_type / space.design_style 1:1."""
    from pipeline.schemas import SpaceClassificationResult as S

    by_dim: dict[str, set] = {}
    for v in load()["gia_tri"]:
        by_dim.setdefault(v["chieu"], set()).add(v["ma_dinh_danh"])

    assert by_dim["khong_gian"] == set(S.model_fields["space_type"].annotation.__args__)
    assert by_dim["phong_cach"] == set(S.model_fields["design_style"].annotation.__args__)
