"""GET /services (change visitor-services-hotspots): the /dich-vu page's packages, in use only, title and text only."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline.store import DSN

TAG = uuid.uuid4().hex[:6]


@pytest.fixture
def entries():
    made = []

    def add(title, content, kind="service", status="dang_dung"):
        with psycopg.connect(DSN) as c:
            made.append(c.execute("INSERT INTO kb_chunk (kind, title, content, trang_thai) VALUES (%s,%s,%s,%s) RETURNING id",
                                  (kind, title, content, status)).fetchone()[0])
        return made[-1]

    yield add
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM kb_chunk WHERE id = ANY(%s)", (made,))


def test_in_use_services_only(entries):
    live = entries(f"TEST dv sống {TAG}", "[DỮ LIỆU MẪU] Thiết kế thử.")
    real = entries(f"TEST dv thật {TAG}", "Mô tả thật.")
    entries(f"TEST dv nháp {TAG}", "nháp", status="nhap")
    entries(f"TEST faq {TAG}", "câu hỏi", kind="faq")
    r = client.get("/services")
    assert r.status_code == 200
    mine = {s["id"]: s for s in r.json() if TAG in s["title"]}
    assert set(mine) == {live, real}
    assert mine[live] == {"id": live, "title": f"TEST dv sống {TAG}", "content": "Thiết kế thử.", "mau": True}
    assert mine[real]["mau"] is False and mine[real]["content"] == "Mô tả thật."
    assert "embedding" not in r.text and "cum_tu_khop" not in r.text
