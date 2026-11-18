"""No prices on the site (the owner's decision, Tùng 9399c77): the assistant never says an amount of money."""
import psycopg
from pgvector.psycopg import register_vector

from pipeline import assistant
from pipeline.store import DSN


def test_without_prices_drops_only_sentences_with_amounts():
    text = "Phòng khách 70m2 dùng gỗ sồi. Chi phí khoảng 500 triệu. Đơn giá 3.5 tr/m2 tùy gói\nLiên hệ để được tư vấn."
    assert assistant.without_prices(text) == "Phòng khách 70m2 dùng gỗ sồi. Liên hệ để được tư vấn."


def test_retrieval_never_returns_price_entries(monkeypatch):
    with psycopg.connect(DSN) as c:
        register_vector(c)
        vec = c.execute("SELECT embedding FROM kb_chunk WHERE embedding IS NOT NULL LIMIT 1").fetchone()
        if not vec:
            return  # no knowledge embedded in this database
        ids = [c.execute("INSERT INTO kb_chunk (kind, title, content, embedding, cum_tu_khop, trang_thai) "
                         "VALUES (%s, %s, %s, %s, '', 'dang_dung') RETURNING id", (kind, title, content, vec[0])).fetchone()[0]
               for kind, title, content in (("price", "Bảng giá zz", "Gói cơ bản từ 5 triệu/m2"),
                                            ("faq", "Chi phí zz", "Căn hộ 70m2 khoảng 500 triệu đồng"))]
    try:
        monkeypatch.setattr(assistant, "_embedder", lambda: type("E", (), {"embed_text": lambda self, q: vec[0].to_list()})())
        got = [r[0] for r in assistant.retrieve("bảng giá chi phí", k=10)]
        assert not set(ids) & set(got)
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM kb_chunk WHERE id = ANY(%s)", (ids,))
