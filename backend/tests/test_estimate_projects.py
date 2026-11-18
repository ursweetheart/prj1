"""visitor-touchpoints 2.2: seq-9 b6-b7 real projects in the same budget range."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import estimate
from pipeline.store import DSN


def test_budget_codes():
    assert estimate.budget_range("duoi_300tr") == (0, 300e6)
    assert estimate.budget_range("300tr_700tr") == (300e6, 700e6)
    assert estimate.budget_range("tren_1500tr")[0] == 1500e6 and estimate.budget_range("tren_1500tr")[1] == float("inf")
    assert estimate.budget_range("khac") is None and estimate.budget_range(None) is None


@pytest.fixture
def projects():
    tag = uuid.uuid4().hex[:6]
    made = {f"zz-ep-apt-{tag}": ("chung-cu", "300tr_700tr", "published"), f"zz-ep-vil-{tag}": ("villa", "300tr_700tr", "published"),
            f"zz-ep-hid-{tag}": ("chung-cu", "300tr_700tr", "draft"), f"zz-ep-far-{tag}": ("chung-cu", "tren_1500tr", "published")}
    with psycopg.connect(DSN) as c:
        for slug, (loai, muc, status) in made.items():
            c.execute("INSERT INTO du_an (slug, ten, loai, muc_dau_tu, thu_tu) VALUES (%s, %s, %s, %s, -1)", (slug, slug, loai, muc))
            c.execute("INSERT INTO space (relative_path, review_status, du_an_slug) VALUES (%s, %s, %s)",
                      (f"zz_ep/{slug}.jpg", status, slug))
    yield list(made)
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE du_an_slug = ANY(%s)", (list(made),))
        c.execute("DELETE FROM du_an WHERE slug = ANY(%s)", (list(made),))


def test_overlap_same_type_first_published_only(projects):
    apt, vil, hid, far = projects
    with psycopg.connect(DSN) as c:
        out = estimate.budget_projects(c, "can_ho", {"min": 500e6, "max": 800e6})
    slugs = [p["slug"] for p in out["ds"]]
    assert out["nhan"] == estimate.BUDGET_LABEL and slugs[:2] == [apt, vil]
    assert hid not in slugs and far not in slugs


def test_fallback_without_budget_data():
    with psycopg.connect(DSN) as c:
        c.execute("SAVEPOINT s")
        c.execute("UPDATE du_an SET muc_dau_tu = NULL")
        out = estimate.budget_projects(c, "can_ho", {"min": 500e6, "max": 800e6})
        c.execute("ROLLBACK TO SAVEPOINT s")
    assert out["nhan"] == estimate.FALLBACK_LABEL and len(out["ds"]) <= 3


def test_estimate_endpoint_carries_the_projects():
    r = client.post("/estimates", json={"loai_nha": "can_ho", "dien_tich_m2": 70, "so_phong_ngu": 2, "goi": "tieu_chuan"})
    assert r.status_code == 200 and r.json()["du_an_goi_y"]["nhan"] in (estimate.BUDGET_LABEL, estimate.FALLBACK_LABEL)
