"""search-explanations 2.1: GET /projects/filter (seq-10, BFD 1.1-1.2). Two throw-away projects with known values."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline.store import DSN


@pytest.fixture
def two():
    tag = uuid.uuid4().hex[:6]
    a, b, hidden = f"zz-pf-a-{tag}", f"zz-pf-b-{tag}", f"zz-pf-h-{tag}"
    with psycopg.connect(DSN) as c:
        for slug, loai, area, style, status in ((a, "chung-cu", 75, "Japandi", "published"), (b, "villa", 300, "Indochine", "published"),
                                                (hidden, "chung-cu", 70, "Japandi", "draft")):
            c.execute("INSERT INTO du_an (slug, ten, loai, dien_tich_m2) VALUES (%s, %s, %s, %s)", (slug, slug.upper(), loai, area))
            c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status, du_an_slug, ngay_xuat_ban) "
                      "VALUES (%s, 'phong_khach', %s, %s, %s, now() - make_interval(days => %s))",
                      (f"zz_pf_{slug}/x.jpg", style, status, slug, 1 if slug == a else 2))
    yield a, b, hidden
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE du_an_slug = ANY(%s)", ([a, b, hidden],))
        c.execute("DELETE FROM du_an WHERE slug = ANY(%s)", ([a, b, hidden],))


def _f(**params):
    r = client.get("/projects/filter", params=params)
    assert r.status_code == 200
    return r.json()


def test_and_across_dimensions_or_within_one_and_area(two):
    a, b, hidden = two
    slugs = lambda r: {p["slug"] for p in r["du_an"]}  # noqa: E731
    r = _f(phong_cach="Japandi", loai_cong_trinh="can_ho", dien_tich_tu=60, dien_tich_den=90)
    assert a in slugs(r) and b not in slugs(r) and hidden not in slugs(r)  # a draft-only project is not published
    assert r["tong"] == len(r["du_an"])
    either = _f(phong_cach=["Japandi", "Indochine"], dien_tich_tu=60)
    assert {a, b} <= slugs(either)


def test_counts_use_the_other_dimensions(two):
    a, b, _ = two
    r = _f(phong_cach="Japandi", dien_tich_tu=60, dien_tich_den=90)
    base = _f(dien_tich_tu=60, dien_tich_den=90)
    assert r["dem"]["phong_cach"]["Japandi"] == base["dem"]["phong_cach"]["Japandi"] >= 1
    assert r["dem"]["loai_cong_trinh"]["biet_thu"] == 0  # villa b is Indochine, 300 m2


def test_loosening_suggestion_when_nothing_matches(two):
    r = _f(phong_cach="Indochine", loai_cong_trinh="can_ho", dien_tich_tu=250, dien_tich_den=400)
    assert r["tong"] == 0 and r["noi_long"]["so_du_an"] >= 1 and r["noi_long"]["chieu"] in ("loai_cong_trinh", "dien_tich", "phong_cach")


def test_sorts(two):
    a, b, _ = two
    newest = [p["slug"] for p in _f(phong_cach=["Japandi", "Indochine"], dien_tich_tu=60)["du_an"]]
    assert newest.index(a) < newest.index(b)  # a was published a day later
    by_area = [p["slug"] for p in _f(phong_cach=["Japandi", "Indochine"], dien_tich_tu=60, sap_xep="dien_tich")["du_an"]]
    assert by_area.index(b) < by_area.index(a)
    assert client.get("/projects/filter", params={"sap_xep": "bogus"}).status_code == 422
