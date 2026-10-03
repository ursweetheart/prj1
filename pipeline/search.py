"""Similarity search over `space` (seq-2). python -m pipeline.search "warm wood bedroom" [space_type]"""

import sys
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from pipeline.store import DSN

COLS = "relative_path, space_type, design_style, 1 - (embedding <=> %(v)s) AS score"


def _query(conn, vec, space_type, k, exclude=None):
    return conn.execute(
        f"SELECT {COLS} FROM space WHERE (%(t)s::text IS NULL OR space_type = %(t)s) "
        "AND (%(x)s::text IS NULL OR relative_path <> %(x)s) ORDER BY embedding <=> %(v)s LIMIT %(k)s",
        {"v": vec, "t": space_type, "k": k, "x": exclude},
    ).fetchall()


def similar_to(relative_path: str, k: int = 6):
    """Same space_type only, so a bedroom never returns a kitchen (seq-2 rule)."""
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        row = conn.execute("SELECT embedding, space_type FROM space WHERE relative_path=%s", (relative_path,)).fetchone()
        return _query(conn, row[0], row[1], k, exclude=relative_path)


def by_text(text: str, space_type: str | None = None, k: int = 6):
    from pipeline.vision_embedder import VisionEmbedder

    vec = np.asarray(VisionEmbedder().embed_text(text), dtype=np.float32)
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        return _query(conn, vec, space_type, k)


if __name__ == "__main__":
    for r in by_text(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(f"{r[3]:.3f}  {r[0]}  {r[1]}  {r[2]}")
