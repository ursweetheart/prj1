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
