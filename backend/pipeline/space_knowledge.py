"""Published photos join the assistant's photo knowledge (publishing-workflow; seq-6 b18). Queued task 'nap_tri_thuc':
a description composed from the photo's reviewed data (no Gemini call, no price) is embedded into space_text."""
from psycopg.rows import tuple_row

from pipeline import intake, vertex
from pipeline.assistant import FORBIDDEN

MODEL = "text-embedding (Vertex, RETRIEVAL_DOCUMENT)"


def compose(conn, space_id: int) -> str | None:
    cur = conn.cursor(row_factory=tuple_row)
    row = cur.execute("SELECT caption, materials, review_status FROM space WHERE id = %s", (space_id,)).fetchone()
    if not row or row[2] != "published":
        return None
    labels = [f"{d}: {v}" for d, v in cur.execute(
        "SELECT c.ten, g.ten FROM space_gia_tri sg JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id "
        "JOIN chieu_phan_loai c ON c.id = g.chieu_id WHERE sg.space_id = %s AND g.ma_dinh_danh NOT ILIKE 'khac' "
        "ORDER BY c.thu_tu", (space_id,)).fetchall()]
    parts = [row[0] or "", ". ".join(labels), ("Vật liệu: " + ", ".join(row[1])) if row[1] else ""]
    # photos only show how a space looks: a sentence naming a price, guarantee or discount is left out (as transcripts)
    sentences = [s.strip().rstrip(".") for p in parts for s in p.split(". ") if s.strip().rstrip(".")]
    kept = [s for s in sentences if not FORBIDDEN.search(s)]
    return ". ".join(kept) + "." if kept else ""


@intake.handler("nap_tri_thuc")
def load(conn, task, ctx):
    return refresh(conn, task["du_lieu"]["space_id"])


@intake.handler("cap_nhat_chi_muc")
def reindex(conn, task, ctx):
    """seq-15 b22 (admin-tools): after a merge, the affected photos' descriptions are written again from their
    current labels, so none names the merged-away value."""
    for sid in task["du_lieu"]["space_ids"]:
        refresh(conn, sid)
    return None


def refresh(conn, sid: int):
    text = compose(conn, sid)
    if text is None:  # taken down before the task ran
        conn.execute("DELETE FROM space_text WHERE space_id = %s", (sid,))
        return sid
    vec = vertex.embed([text], "RETRIEVAL_DOCUMENT")[0]
    import numpy as np
    from pgvector.psycopg import register_vector
    register_vector(conn)
    conn.execute("INSERT INTO space_text (space_id, transcript, embedding, mo_hinh) VALUES (%s, %s, %s, %s) "
                 "ON CONFLICT (space_id) DO UPDATE SET transcript = EXCLUDED.transcript, embedding = EXCLUDED.embedding, "
                 "mo_hinh = EXCLUDED.mo_hinh", (sid, text, np.asarray(vec, dtype=np.float32), MODEL))
    return sid


def backfill(conn) -> int:
    """Queue every published photo without a description yet (photos published before this change)."""
    ids = [r[0] for r in conn.cursor(row_factory=tuple_row).execute(
        "SELECT s.id FROM space s WHERE s.review_status = 'published' AND NOT EXISTS "
        "(SELECT 1 FROM space_text t WHERE t.space_id = s.id) AND NOT EXISTS (SELECT 1 FROM hang_doi_tac_vu q "
        " WHERE q.loai = 'nap_tri_thuc' AND q.trang_thai IN ('cho', 'dang_xu_ly') AND (q.du_lieu->>'space_id')::int = s.id) "
        "ORDER BY s.id").fetchall()]
    for sid in ids:
        intake.enqueue(conn, "nap_tri_thuc", {"space_id": sid})
    return len(ids)


if __name__ == "__main__":  # python -m pipeline.space_knowledge --backfill
    import sys

    import psycopg

    from pipeline.store import DSN
    if "--backfill" not in sys.argv:
        raise SystemExit("usage: python -m pipeline.space_knowledge --backfill")
    with psycopg.connect(DSN) as c:
        print(f"queued {backfill(c)} published photo(s) for the assistant's knowledge; the API's queue worker runs them")
