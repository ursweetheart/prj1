"""Style quiz (UC06, seq-12): pairs of published photos in two different styles, scored on the server, suggestions by
SigLIP2 embedding centroid. Stateless: the client sends back the pairs it was shown, and every id is re-checked here,
so the only thing a visitor can invent is their own result.

    build_pairs(spaces, rnd)   -> [(a, b), ...]   pure; spaces are (id, style, space_type)
    check(conn, pairs, chosen) -> (shown {style: n}, chosen styles)   raises Invalid (-> 422)
    score(shown, chosen)       -> [{ma, ti_le, diem}], best 2 first
    suggest(conn, chosen, shown_ids, styles) -> published tiles of those styles, closest to the chosen photos first"""

from collections import Counter, defaultdict

from psycopg.rows import tuple_row

QUESTIONS, MIN_QUESTIONS, MIN_PER_STYLE, MIN_CHOSEN, TOP_STYLES, SUGGESTIONS = 6, 4, 2, 2, 2, 8
ELIGIBLE = ("SELECT id, design_style, space_type FROM space WHERE review_status = 'published' "
            "AND design_style IS NOT NULL AND lower(design_style) <> 'khac'")
TILE = "id, relative_path, space_type, design_style, alt_text, caption"


class Invalid(ValueError):
    """An answer set the server will not score (the endpoint answers 422)."""


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def eligible(conn) -> list:
    return _rows(conn, ELIGIBLE)


def build_pairs(spaces, rnd, n: int = QUESTIONS) -> list:
    """Up to n pairs (a, b) of distinct photos in two different styles; [] when fewer than MIN_QUESTIONS are possible.
    Styles are shown as evenly as their photos allow; a pair keeps to one space type when both styles have it."""
    by_style = defaultdict(list)
    for sid, style, room in spaces:
        if style and style.lower() != "khac":
            by_style[style].append((sid, room or ""))
    by_style = {s: p for s, p in by_style.items() if len(p) >= MIN_PER_STYLE}
    if len(by_style) < 2:
        return []

    # 1. share out the 2n photo slots: always to a style with the fewest slots that still has an unused photo
    slots = dict.fromkeys(by_style, 0)
    for _ in range(2 * n):
        open_ = [s for s in by_style if slots[s] < len(by_style[s])]
        if not open_:
            break
        low = min(slots[s] for s in open_)
        slots[rnd.choice(sorted(s for s in open_ if slots[s] == low))] += 1

    # 2. pair the slots, the style with most slots left against the next one: gives min(T // 2, T - M) pairs
    left, style_pairs = dict(slots), []
    while len(style_pairs) < n:
        active = sorted((s for s in left if left[s] > 0), key=lambda s: (-left[s], rnd.random()))
        if len(active) < 2:
            break
        a, b = active[0], active[1]
        left[a] -= 1
        left[b] -= 1
        style_pairs.append((a, b))
    if len(style_pairs) < MIN_QUESTIONS:
        return []

    # 3. photos: a space type both styles still have (the most plentiful), otherwise any unused photo
    unused = {s: rnd.sample(p, len(p)) for s, p in by_style.items()}
    pairs = []
    for a, b in style_pairs:
        rooms_a, rooms_b = Counter(r for _, r in unused[a]), Counter(r for _, r in unused[b])
        common = sorted(set(rooms_a) & set(rooms_b), key=lambda r: (-(rooms_a[r] + rooms_b[r]), rnd.random()))
        pick = []
        for s in (a, b):
            i = next((k for k, (_, r) in enumerate(unused[s]) if r == common[0]), 0) if common else 0
            pick.append(unused[s].pop(i)[0])
        pairs.append(tuple(rnd.sample(pick, 2)))  # random left / right
    rnd.shuffle(pairs)
    return pairs


def check(conn, pairs, chosen):
    """Validate an answer set against the database. Returns ({style: times shown}, [style of each chosen photo])."""
    if not 1 <= len(pairs) <= QUESTIONS:
        raise Invalid(f"1 to {QUESTIONS} pairs")
    if len(chosen) < MIN_CHOSEN:
        raise Invalid(f"choose at least {MIN_CHOSEN} photos")
    shown_ids = [i for p in pairs for i in p]
    if any(len(p) != 2 for p in pairs) or len(set(shown_ids)) != len(shown_ids):
        raise Invalid("each pair holds two photos, and no photo is shown twice")
    pair_of = {i: k for k, p in enumerate(pairs) for i in p}
    if any(c not in pair_of for c in chosen):
        raise Invalid("a chosen photo was not in any pair")
    if len({pair_of[c] for c in chosen}) != len(chosen):
        raise Invalid("one photo per pair")
    style = {sid: s for sid, s, _ in _rows(conn, ELIGIBLE + " AND id = ANY(%s)", (shown_ids,))}
    if len(style) != len(shown_ids):
        raise Invalid("every photo must be a published space with a style")
    if any(style[a] == style[b] for a, b in pairs):
        raise Invalid("the two photos of a pair have different styles")
    return Counter(style[i] for i in shown_ids), [style[c] for c in chosen]


def score(shown: dict, chosen_styles: list) -> list:
    """points / times shown per style; the best TOP_STYLES with a point, each with its share (%) of all style scores."""
    points = Counter(chosen_styles)
    scores = {s: points[s] / n for s, n in shown.items() if n}
    total = sum(scores.values())
    best = sorted((s for s in scores if points[s]), key=lambda s: (-scores[s], -points[s], s))[:TOP_STYLES]
    return [{"ma": s, "diem": round(scores[s], 4), "ti_le": round(100 * scores[s] / total)} for s in best]


def suggest(conn, chosen, shown_ids, styles, k: int = SUGGESTIONS) -> list:
    """Published spaces of `styles` not shown in the quiz, by cosine distance to the mean embedding of the chosen photos."""
    rows = _rows(
        conn, f"WITH c AS (SELECT avg(embedding) v FROM space WHERE id = ANY(%(c)s) AND embedding IS NOT NULL) "
        f"SELECT {', '.join('s.' + col.strip() for col in TILE.split(','))} FROM space s, c "
        "WHERE s.review_status = 'published' AND s.design_style = ANY(%(st)s) AND s.id <> ALL(%(sh)s) "
        "AND s.embedding IS NOT NULL ORDER BY s.embedding <=> c.v NULLS LAST, s.id LIMIT %(k)s",
        {"c": list(chosen), "st": list(styles), "sh": list(shown_ids), "k": k})
    return [_tile(r) for r in rows]


def suggest_projects(conn, chosen, styles, k: int = 3) -> list:
    """project-catalog: catalog projects with published photos of `styles`, most such photos first, then the one whose
    closest photo is nearest the mean of the chosen photos. Each: slug, ten, co_trang, phong_cach (its most common
    matching style) and that closest photo."""
    rows = _rows(conn, """
        WITH c AS (SELECT avg(embedding) v FROM space WHERE id = ANY(%(c)s) AND embedding IS NOT NULL),
             m AS (SELECT s.du_an_slug, s.id, s.relative_path, s.anh_trang, s.design_style, s.embedding <=> c.v AS d
                     FROM space s, c WHERE s.review_status = 'published' AND s.design_style = ANY(%(st)s)
                      AND s.du_an_slug IS NOT NULL AND s.embedding IS NOT NULL)
        SELECT p.slug, p.ten, p.co_trang, mode() WITHIN GROUP (ORDER BY m.design_style),
               (array_agg(json_build_object('id', m.id, 'relative_path', m.relative_path, 'anh_trang', m.anh_trang)
                          ORDER BY m.d NULLS LAST, m.id))[1]
          FROM m JOIN du_an p ON p.slug = m.du_an_slug
         GROUP BY p.slug ORDER BY count(*) DESC, min(m.d) NULLS LAST, p.slug LIMIT %(k)s""",
                 {"c": list(chosen), "st": list(styles), "k": k})
    return [dict(zip(("slug", "ten", "co_trang", "phong_cach", "anh"), r)) for r in rows]


def tiles(conn, ids) -> list:
    """Published spaces among ids, in the given order (a saved result re-read: unpublished ones are dropped)."""
    rows = {r[0]: r for r in _rows(conn, f"SELECT {TILE} FROM space WHERE review_status = 'published' AND id = ANY(%s)",
                                   (list(ids),))}
    return [_tile(rows[i]) for i in ids if i in rows]


def _tile(r) -> dict:
    return dict(zip(("id", "relative_path", "space_type", "design_style", "alt_text", "caption"), r))


def style_names(conn) -> dict:
    return dict(_rows(conn, "SELECT g.ma_dinh_danh, g.ten FROM gia_tri_phan_loai g JOIN chieu_phan_loai d "
                            "ON d.id = g.chieu_id WHERE d.ma_dinh_danh = 'phong_cach'"))


def result(conn, pairs, chosen) -> dict:
    """The full answer: styles with names and shares, and the suggested spaces. Raises Invalid."""
    shown, chosen_styles = check(conn, pairs, chosen)
    best = score(shown, chosen_styles)
    names = style_names(conn)
    styles = [{"ma": b["ma"], "ten": names.get(b["ma"], b["ma"]), "ti_le": b["ti_le"]} for b in best]
    goi_y = suggest(conn, chosen, [i for p in pairs for i in p], [b["ma"] for b in best])
    return {"phong_cach": styles, "goi_y": goi_y, "du_an": suggest_projects(conn, chosen, [b["ma"] for b in best])}
