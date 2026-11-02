"""Needs Postgres up + ingested data: docker compose up -d && python ingest.py image_d3"""
import psycopg
from pipeline.search import similar_to, by_text
from pipeline.store import DSN


def test_similar_same_space_type_and_excludes_self():
    with psycopg.connect(DSN) as c:
        path, st = c.execute("SELECT relative_path, space_type FROM space WHERE space_type='phong_ngu_master' LIMIT 1").fetchone()
    res = similar_to(path, k=5)
    assert res and all(r[1] == st and r[0] != path for r in res)


def test_text_search_filters_space_type():
    res = by_text("phòng ngủ ấm áp tông gỗ", "phong_ngu_master", k=5)
    assert res and all(r[1] == "phong_ngu_master" for r in res)


# ── photo search (search-by-image) ───────────────────────────────────────────
import io

import numpy as np
from PIL import Image
from pgvector.psycopg import register_vector

from pipeline.search import DUP_SCORE, PER_PROJECT, by_image


def _photo(img, fmt="JPEG", **kw):
    buf = io.BytesIO()
    img.save(buf, fmt, **kw)
    buf.seek(0)
    return buf


def _embeddings(ids):
    with psycopg.connect(DSN) as c:
        register_vector(c)
        rows = {i: (e, s) for i, e, s in c.execute("SELECT id, embedding, subfolder FROM space WHERE id = ANY(%s)", (ids,))}
    return [rows[i][0].to_numpy() for i in ids], [rows[i][1] for i in ids]


def test_photo_search_finds_the_original_and_keeps_results_varied():
    with psycopg.connect(DSN) as c:
        register_vector(c)
        path, orig = c.execute("SELECT relative_path, embedding FROM space WHERE space_type='phong_khach' ORDER BY id LIMIT 1").fetchone()
    img = Image.open("image_d3/" + path).convert("RGB")
    w, h = img.size
    reshot = img.crop((w * .1, h * .1, w * .9, h * .9)).resize((640, int(640 * h / w)))  # a phone re-shot, roughly
    res = by_image(_photo(reshot, quality=60), k=12)
    embs, subs = _embeddings([r[4] for r in res])
    assert res[0][0] == path or np.dot(embs[0], orig.to_numpy()) >= DUP_SCORE
    assert [r[3] for r in res] == sorted((r[3] for r in res), reverse=True)
    assert max(subs.count(s) for s in subs) <= PER_PROJECT
    assert all(np.dot(a, b) < DUP_SCORE for i, a in enumerate(embs) for b in embs[i + 1:])


def test_photo_search_rejects_a_non_interior_photo():
    assert by_image(_photo(Image.new("RGB", (400, 400), (120, 120, 120)), "PNG")) == []


def test_photo_search_filters_space_type():
    img = Image.open("../public/img/pic3.jpg").convert("RGB")
    res = by_image(_photo(img), "phong_khach", k=12)
    assert res and all(r[1] == "phong_khach" for r in res)
