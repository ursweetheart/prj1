"""visitor-touchpoints 2.1: BFD 2.3 "Chia sẻ bộ sưu tập" as a read-only snapshot."""
import psycopg

import ratelimit

from conftest import client
from pipeline.store import DSN


def _ids(status, n):
    with psycopg.connect(DSN) as c:
        return [r[0] for r in c.execute("SELECT id FROM space WHERE review_status=%s ORDER BY id LIMIT %s", (status, n))]


def _drop(code):
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM bo_suu_tap WHERE ma_chia_se=%s", (code,))


def test_share_keeps_published_photos_and_does_not_follow_later_changes():
    pub, draft = _ids("published", 2), _ids("draft", 1)
    r = client.post("/collections/share", json={"items": [{"space_id": pub[0], "ghi_chu": "thích sàn gỗ"},
                                                          {"space_id": draft[0]}, {"space_id": pub[1]}]})
    assert r.status_code == 201 and r.json()["so_anh"] == 2
    code = r.json()["ma"]
    try:
        view = client.get(f"/collections/shared/{code}").json()
        assert [i["id"] for i in view["items"]] == pub and view["items"][0]["ghi_chu"] == "thích sàn gỗ"
        assert view["tom_tat"] is None
        again = client.get(f"/collections/shared/{code}").json()  # nothing the visitor does later changes it
        assert [i["id"] for i in again["items"]] == pub
    finally:
        _drop(code)


def test_share_limits():
    assert client.post("/collections/share", json={"items": [{"space_id": i} for i in range(61)]}).status_code == 422
    assert client.post("/collections/share", json={"items": [{"space_id": _ids("draft", 1)[0]}]}).status_code == 422
    codes = []
    pub = _ids("published", 1)[0]
    ratelimit.reset()  # the two refused requests above count too
    try:
        statuses = []
        for _ in range(11):
            r = client.post("/collections/share", json={"items": [{"space_id": pub}]})
            statuses.append(r.status_code)
            if r.status_code == 201:
                codes.append(r.json()["ma"])
        assert statuses[:10] == [201] * 10 and statuses[10] == 429
    finally:
        for c in codes:
            _drop(c)
