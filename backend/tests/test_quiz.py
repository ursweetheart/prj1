"""Style quiz (change style-quiz): pairs, scoring, answer checks, suggestions, endpoints, quiz events.
Throw-away spaces use made-up styles ('Tq_…'), so the real published photos never change and never interfere."""
import random
import uuid
from collections import Counter

import psycopg
import pytest

import api
from conftest import client
from pipeline import quiz
from pipeline.store import DSN


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


def _vec(*head):
    v = list(head) + [0.0] * (768 - len(head))
    return "[" + ",".join(str(x) for x in v) + "]"


@pytest.fixture
def spaces():
    """spaces(style, n, room=..., vec=..., status=...) -> ids of throw-away spaces, deleted afterwards."""
    made = []

    def make(style, n=1, room="phong_khach", vec=None, status="published"):
        ids = []
        with psycopg.connect(DSN) as c:
            for _ in range(n):
                ids.append(c.execute(
                    "INSERT INTO space (relative_path, space_type, design_style, review_status, embedding) "
                    "VALUES (%s,%s,%s,%s,%s::vector) RETURNING id",
                    (f"test_quiz_{uuid.uuid4().hex[:8]}/x.jpg", room, style, status, vec or _vec(1.0))).fetchone()[0])
        made.extend(ids)
        return ids

    yield make
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made,))


def _pool(**styles):  # style=count (all phong_khach) -> (id, style, room) tuples for build_pairs
    pool, n = [], 0
    for style, count in styles.items():
        for _ in range(count):
            n += 1
            pool.append((n, style, "phong_khach"))
    return pool


# ── 1.1 quiz events ────────────────────────────────────────────────────────────
def test_consented_quiz_pick_is_stored_with_snapshot(spaces):
    sid, pid = spaces("Japandi")[0], "t" + uuid.uuid4().hex
    try:
        r = client.post("/events", json={"loai": "chon_trac_nghiem", "dong_y": True, "phien_id": pid, "space_id": sid})
        assert r.status_code == 204
        loai, tags = _q("SELECT loai, gia_tri FROM su_kien WHERE phien_id=%s", pid)[0]
        assert loai == "chon_trac_nghiem" and "phong_cach:Japandi" in tags
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM phien_truy_cap WHERE id=%s", (pid,))


def test_quiz_pick_without_consent_counts_anonymously():
    sql = "SELECT COALESCE(sum(so_luong),0) FROM su_kien_an_danh WHERE ngay=(now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AND loai='chon_trac_nghiem'"
    before = _q(sql)[0][0]
    assert client.post("/events", json={"loai": "chon_trac_nghiem", "dong_y": False}).status_code == 204
    assert _q(sql)[0][0] == before + 1
    with psycopg.connect(DSN) as c:
        c.execute("UPDATE su_kien_an_danh SET so_luong = so_luong - 1 WHERE ngay=(now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AND loai='chon_trac_nghiem'")


# ── 2.1 pairs ──────────────────────────────────────────────────────────────────
def test_balanced_pairs_today_shape():
    pool = _pool(Indochine=13, Luxury=13, Hien_dai=8, Japandi=6)
    style = {i: s for i, s, _ in pool}
    pairs = quiz.build_pairs(pool, random.Random(1))
    ids = [i for p in pairs for i in p]
    assert len(pairs) == 6 and len(set(ids)) == 12
    assert all(style[a] != style[b] for a, b in pairs)
    assert Counter(style[i] for i in ids) == {"Indochine": 3, "Luxury": 3, "Hien_dai": 3, "Japandi": 3}


def test_pairs_keep_to_one_space_type():
    pool = [(n, s, room) for n, (s, room) in enumerate(
        [(s, r) for s in ("A", "B", "C") for r in ("bep", "phong_ngu", "phong_khach") for _ in range(2)])]
    room = {i: r for i, _, r in pool}
    for seed in range(20):
        assert all(room[a] == room[b] for a, b in quiz.build_pairs(pool, random.Random(seed)))


def test_uneven_styles_not_enough_pairs():
    assert quiz.build_pairs(_pool(Indochine=13, Japandi=3), random.Random(1)) == []  # at most 3 pairs
    assert quiz.build_pairs(_pool(Indochine=40), random.Random(1)) == []             # one style


def test_one_photo_style_and_khac_never_shown():
    pool = _pool(A=4, B=4, C=4, Wabi=1, Khac=10, khac=3)
    style = {i: s for i, s, _ in pool}
    for seed in range(20):
        shown = {style[i] for p in quiz.build_pairs(pool, random.Random(seed)) for i in p}
        assert shown <= {"A", "B", "C"}


def test_different_seeds_different_pairs():
    pool = _pool(A=10, B=10, C=10, D=10)
    assert quiz.build_pairs(pool, random.Random(1)) != quiz.build_pairs(pool, random.Random(2))


# ── 2.2 score and checks ───────────────────────────────────────────────────────
def test_score_spec_example():
    shown = {"Japandi": 3, "Hien_dai": 3, "Luxury": 3, "Indochine": 3}
    picks = ["Japandi"] * 3 + ["Hien_dai"] * 2 + ["Luxury"]
    assert [(b["ma"], b["ti_le"]) for b in quiz.score(shown, picks)] == [("Japandi", 50), ("Hien_dai", 33)]


def test_score_single_style():
    assert [(b["ma"], b["ti_le"]) for b in quiz.score({"Indochine": 3, "Luxury": 3}, ["Indochine"] * 2)] == \
        [("Indochine", 100)]


def test_checks_reject_bad_answers(spaces):
    a, b, c, d = spaces("Tq_a", 2) + spaces("Tq_b", 2)
    draft = spaces("Tq_a", 1, status="draft")[0]
    with psycopg.connect(DSN) as conn:
        shown, picked = quiz.check(conn, [[a, c], [b, d]], [a, d])
        assert shown == {"Tq_a": 2, "Tq_b": 2} and picked == ["Tq_a", "Tq_b"]
        for pairs, chosen in [
            ([[a, c], [b, d]], [a, 99999999]),     # not in any pair
            ([[a, c], [b, d]], [a, c]),            # two picks from one pair
            ([[a, c], [a, d]], [a, d]),            # photo shown twice
            ([[a, c], [b, d]], [a]),               # fewer than 2 picks
            ([[a, c]] * 7, [a, c]),                # more than 6 pairs
            ([[a, b], [c, d]], [a, c]),            # same style in a pair
            ([[a, c], [draft, d]], [a, d]),        # unpublished photo
        ]:
            with pytest.raises(quiz.Invalid):
                quiz.check(conn, pairs, chosen)


# ── 2.3 suggestions ────────────────────────────────────────────────────────────
def test_suggest_closest_published_unshown(spaces):
    c1, c2 = spaces("Tq_s", 2, vec=_vec(1.0, 0.0))
    near = spaces("Tq_s", 1, vec=_vec(0.95, 0.05))[0]
    mid = spaces("Tq_t", 1, vec=_vec(0.6, 0.4))[0]
    far = spaces("Tq_s", 1, vec=_vec(0.0, 1.0))[0]
    hidden = spaces("Tq_s", 1, vec=_vec(1.0, 0.0), status="draft")[0]
    other_style = spaces("Tq_other", 1, vec=_vec(1.0, 0.0))[0]
    with psycopg.connect(DSN) as conn:
        got = [t["id"] for t in quiz.suggest(conn, [c1, c2], [c1, c2], ["Tq_s", "Tq_t"])]
    assert got == [near, mid, far]
    assert hidden not in got and other_style not in got and c1 not in got


# ── 3.1 endpoints ──────────────────────────────────────────────────────────────
def test_get_quiz_and_round_trip():
    r = client.get("/quiz")
    if r.status_code == 409:
        pytest.skip("fewer than 4 pairs of published photos in this database")
    pairs = r.json()["cau_hoi"]
    ids = [t["id"] for p in pairs for t in (p["a"], p["b"])]
    assert 4 <= len(pairs) <= 6 and len(set(ids)) == len(ids)
    assert {s for (s,) in _q("SELECT review_status FROM space WHERE id = ANY(%s)", ids)} == {"published"}
    body = {"cap": [[p["a"]["id"], p["b"]["id"]] for p in pairs], "chon": [p["a"]["id"] for p in pairs]}
    out = client.post("/quiz/result", json=body).json()
    assert 1 <= len(out["phong_cach"]) <= 2 and all(s["ten"] and s["ti_le"] > 0 for s in out["phong_cach"])
    assert len(out["goi_y"]) <= 8 and not set(t["id"] for t in out["goi_y"]) & set(ids)
    assert {t["design_style"] for t in out["goi_y"]} <= {s["ma"] for s in out["phong_cach"]}


def test_result_rejects_forged_and_unpublished(spaces):
    a, b = spaces("Tq_a", 2)
    c, d = spaces("Tq_b", 2)
    draft = spaces("Tq_b", 1, status="draft")[0]
    ok = {"cap": [[a, c], [b, d]], "chon": [a, d]}
    assert client.post("/quiz/result", json=ok).status_code == 200
    assert client.post("/quiz/result", json={**ok, "chon": [a, 99999999]}).status_code == 422
    assert client.post("/quiz/result", json={"cap": [[a, c], [b, draft]], "chon": [a, b]}).status_code == 422


def test_get_quiz_409_with_one_style(monkeypatch):
    monkeypatch.setattr(api.quiz, "eligible", lambda conn: _pool(Indochine=20))
    r = client.get("/quiz")
    assert r.status_code == 409 and r.json()["detail"] == "chua_du_anh"


# ── 3.2 saved result ───────────────────────────────────────────────────────────
def test_saved_result_per_account(spaces, as_role):
    a, b = spaces("Tq_a", 2, vec=_vec(1.0))
    c, d = spaces("Tq_b", 2, vec=_vec(1.0))
    extra = spaces("Tq_a", 1, vec=_vec(1.0))[0]
    extra_b = spaces("Tq_b", 1, vec=_vec(1.0))[0]
    me, other = as_role("visitor"), as_role("visitor")
    first = {"cap": [[a, c], [b, d]], "chon": [a, b]}
    assert client.get("/quiz/me").status_code == 401
    assert client.put("/quiz/me", json=first).status_code == 401
    assert client.get("/quiz/me", headers=me).status_code == 204
    saved = client.put("/quiz/me", json=first, headers=me).json()
    assert saved["phong_cach"][0]["ma"] == "Tq_a" and extra in [t["id"] for t in saved["goi_y"]]
    got = client.get("/quiz/me", headers=me).json()
    assert got["phong_cach"] == saved["phong_cach"] and [t["id"] for t in got["goi_y"]] == [t["id"] for t in saved["goi_y"]]
    assert client.get("/quiz/me", headers=other).status_code == 204          # nobody else sees it
    second = client.put("/quiz/me", json={"cap": [[a, c], [b, d]], "chon": [c, d]}, headers=me).json()
    assert second["phong_cach"][0]["ma"] == "Tq_b"
    assert client.get("/quiz/me", headers=me).json()["phong_cach"][0]["ma"] == "Tq_b"  # replaced, one per account
    assert [t["id"] for t in client.get("/quiz/me", headers=me).json()["goi_y"]][:1] == [extra_b]
    with psycopg.connect(DSN) as conn:  # a suggestion unpublished later is dropped on read
        conn.execute("UPDATE space SET review_status='draft' WHERE id=%s", (extra_b,))
    assert extra_b not in [t["id"] for t in client.get("/quiz/me", headers=me).json()["goi_y"]]
    assert client.put("/quiz/me", json={**first, "chon": [a, 99999999]}, headers=me).status_code == 422


# ── project-catalog 4.3: projects in the result ────────────────────────────────────────────────────────────────
def test_suggested_projects_ranked_by_matching_photos_then_closeness(spaces):
    chosen = spaces("Tq_p", 1, vec=_vec(1.0, 0.0))
    a1, a2 = spaces("Tq_p", 2, vec=_vec(0.0, 1.0))             # project A: two matching photos, both far
    b1 = spaces("Tq_q", 1, vec=_vec(0.99, 0.01))[0]           # project B: one matching photo, very close
    b_draft = spaces("Tq_p", 1, vec=_vec(1.0, 0.0), status="draft")[0]
    c_other = spaces("Tq_other", 3, vec=_vec(1.0, 0.0))       # project C: other style only
    with psycopg.connect(DSN) as c:
        for slug in ("zzt-qa", "zzt-qb", "zzt-qc"):
            c.execute("INSERT INTO du_an (slug, ten, co_trang) VALUES (%s, %s, true)", (slug, slug.upper()))
        for slug, ids in (("zzt-qa", [a1, a2]), ("zzt-qb", [b1, b_draft]), ("zzt-qc", c_other)):
            c.execute("UPDATE space SET du_an_slug = %s WHERE id = ANY(%s)", (slug, ids))
    try:
        with psycopg.connect(DSN) as conn:
            got = quiz.suggest_projects(conn, chosen, ["Tq_p", "Tq_q"])
            assert [(p["slug"], p["phong_cach"], p["anh"]["id"]) for p in got] == [("zzt-qa", "Tq_p", a1), ("zzt-qb", "Tq_q", b1)]
            assert got[0]["ten"] == "ZZT-QA" and got[0]["co_trang"] is True
            assert quiz.suggest_projects(conn, chosen, ["Tq_none"]) == []
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("UPDATE space SET du_an_slug = NULL WHERE du_an_slug LIKE 'zzt-q%'")
            c.execute("DELETE FROM du_an WHERE slug LIKE 'zzt-q%'")
