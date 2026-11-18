"""Project catalog helpers (change: project-catalog 2.1). No network, no database."""

import pytest

from pipeline import projects as pj


def test_reads_the_real_site_list():
    ps = pj.parse_site_projects(pj.SITE_JS.read_text(encoding="utf-8"))
    assert len(ps) == 64 and len({p["slug"] for p in ps}) == 64
    assert ps[0] == {"slug": "uri-lounge", "ten": "URI Lounge", "loai": "lounge", "nam": None, "mo_ta_ngan": None, "thu_tu": 1}
    assert ps[1]["ten"] == "Indochine – Chinoiserie Villa"


def test_optional_fields_and_a_quote():
    ps = pj.parse_site_projects("const PROJECTS = [\n  { slug: 'a-b', loai: 'villa', name: 'O\\'Neil', year: 2023, brief: 'Hai tầng' },\n]")
    assert ps == [{"slug": "a-b", "ten": "O'Neil", "loai": "villa", "nam": 2023, "mo_ta_ngan": "Hai tầng", "thu_tu": 1}]


@pytest.mark.parametrize("text", [
    "const X = []",                                                        # no list
    "const PROJECTS = [\n]",                                               # empty
    "const PROJECTS = [\n  { slug: 'a', name: 'A' },\n  slug: 'b',\n]",    # a broken line
    "const PROJECTS = [\n  { slug: 'Bad Slug', name: 'A' },\n]",           # bad slug
])
def test_malformed_lists_are_refused(text):
    with pytest.raises(ValueError):
        pj.parse_site_projects(text)


def _unit(*v):
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v]


def test_match_keeps_mutual_pairs_above_the_threshold():
    a, b = _unit(1, 0, 0), _unit(0, 1, 0)
    site = {"s1": a, "s2": _unit(0, 1, 0.38), "s3": _unit(0, 1, 0.3)}  # s2 ~0.935 to b; s3 ~0.958 to b
    pairs, near = pj.match(site, {1: a, 2: b})
    assert [(k, i) for k, i, _ in pairs] == [("s1", 1), ("s3", 2)]
    assert [(k, i) for k, i, _ in near] == [("s2", 2)]  # b's best is s3: s2 is one-way, and below the bar anyway


def test_one_way_best_is_not_a_match():
    a = _unit(1, 0)
    pairs, _ = pj.match({"x": a, "y": _unit(1, 0.05)}, {1: _unit(1, 0.04)})
    assert [(k, i) for k, i, _ in pairs] == [("y", 1)]  # only y and space 1 pick each other


def test_folder_project_slug():
    assert pj.folder_project_slug("Indochine", {"indochine"}) == "indochine-thu-muc"
    assert pj.folder_project_slug("nha_anh_tuan", set()) == "nha-anh-tuan"


# ── 2.3: the sync against the database, inside one rolled-back transaction (the real catalog is never touched) ─────
import uuid  # noqa: E402

import numpy as np  # noqa: E402
import psycopg  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

import sync_projects as sp  # noqa: E402
from pipeline.store import DSN  # noqa: E402


@pytest.fixture
def conn():
    c = psycopg.connect(DSN)
    register_vector(c)
    yield c
    c.rollback()
    c.close()


def e(i):
    v = np.zeros(768)
    v[700 + i] = 1.0
    return v


def site(*slugs):
    return [{"slug": s, "ten": s.upper(), "loai": "villa", "nam": None, "mo_ta_ngan": None, "thu_tu": n} for n, s in enumerate(slugs, 1)]


def space(c, folder, vec, **cols):
    keys = ", ".join(["relative_path", "embedding", *cols])
    marks = ", ".join(["%s"] * (2 + len(cols)))
    return c.execute(f"INSERT INTO space ({keys}) VALUES ({marks}) RETURNING id",
                     (f"{folder}/{uuid.uuid4().hex[:8]}.jpg", vec, *cols.values())).fetchone()[0]


def slug_of(c, sid):
    return c.execute("SELECT du_an_slug, anh_trang FROM space WHERE id = %s", (sid,)).fetchone()


def test_match_link_majority_and_folder_project(conn):
    a, b, left = space(conn, "zzt_old", e(1)), space(conn, "zzt_old", e(2)), space(conn, "zzt_old", e(3))
    lone = space(conn, "zzt_Lone", e(4))
    r = sp.run(conn, site("zzt-villa"), {"zzt-villa": ["01.jpg", "02.jpg", "03.jpg"]},
               {("zzt-villa", "01.jpg"): e(1), ("zzt-villa", "02.jpg"): e(2), ("zzt-villa", "03.jpg"): e(9)})
    assert slug_of(conn, a) == ("zzt-villa", "01.jpg") and slug_of(conn, b) == ("zzt-villa", "02.jpg")
    assert slug_of(conn, left) == ("zzt-villa", None)          # a leftover follows its folder's majority
    assert ("zzt-villa", "03.jpg") in r["unmatched"]
    assert slug_of(conn, lone) == ("zzt-lone", None)            # no match: the folder's own project, no page
    assert conn.execute("SELECT ten, co_trang FROM du_an WHERE slug = 'zzt-lone'").fetchone() == ("zzt_Lone", False)
    assert conn.execute("SELECT count(*) FROM nhat_ky_du_an WHERE hanh_dong = 'lien_ket' AND du_an_slug = 'zzt-villa'").fetchone()[0] == 2


def test_rerun_changes_nothing_and_keeps_staff_fields(conn):
    space(conn, "zzt_old", e(1))
    args = (site("zzt-villa"), {"zzt-villa": ["01.jpg"]}, {("zzt-villa", "01.jpg"): e(1)})
    sp.run(conn, *args)
    conn.execute("UPDATE du_an SET dien_tich_m2 = 120 WHERE slug = 'zzt-villa'")
    logs = conn.execute("SELECT count(*) FROM nhat_ky_du_an").fetchone()[0]
    renamed = [{**site("zzt-villa")[0], "ten": "Villa II"}]
    assert sp.run(conn, renamed, *args[1:])["linked"] == 0
    assert conn.execute("SELECT count(*) FROM nhat_ky_du_an").fetchone()[0] == logs
    assert conn.execute("SELECT ten, dien_tich_m2, co_trang FROM du_an WHERE slug = 'zzt-villa'").fetchone() == ("Villa II", 120, True)


def test_existing_link_is_not_overwritten_and_dropped_projects_lose_their_page(conn):
    conn.execute("INSERT INTO du_an (slug, ten, thu_tu, co_trang) VALUES ('zzt-gone', 'Gone', 99, true)")
    kept = space(conn, "zzt_x", e(1), du_an_slug="zzt-gone")
    sp.run(conn, site("zzt-villa"), {"zzt-villa": ["01.jpg"]}, {("zzt-villa", "01.jpg"): e(1)})
    assert slug_of(conn, kept) == ("zzt-gone", None)
    assert conn.execute("SELECT co_trang, thu_tu FROM du_an WHERE slug = 'zzt-gone'").fetchone() == (False, None)


def test_slug_named_folder_goes_to_its_site_project(conn):
    sid = space(conn, "zzt_villa", e(5))
    sp.run(conn, site("zzt-villa"), {"zzt-villa": ["01.jpg"]}, {("zzt-villa", "01.jpg"): e(1)})
    assert slug_of(conn, sid)[0] == "zzt-villa"
    assert not conn.execute("SELECT 1 FROM du_an WHERE slug = 'zzt-villa-thu-muc'").fetchone()
