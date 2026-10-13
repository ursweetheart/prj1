"""Similarity search over `space` (seq-2). python -m pipeline.search "warm wood bedroom" [space_type]"""

import sys
from functools import lru_cache
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from pipeline.store import DSN

COLS = "relative_path, space_type, design_style, 1 - (embedding <=> %(v)s) AS score, id"


MAX_K = 24


@lru_cache(maxsize=1)
def _embedder():  # load the model once per process, not per query
    from pipeline.vision_embedder import VisionEmbedder
    return VisionEmbedder()


def _query(conn, vec, space_type, k, exclude=None, published_only=False):
    k = max(1, min(k, MAX_K))
    return conn.execute(
        f"SELECT {COLS} FROM space WHERE (%(t)s::text IS NULL OR space_type = %(t)s) "
        "AND (%(x)s::text IS NULL OR relative_path <> %(x)s) AND (NOT %(p)s OR review_status = 'published') ORDER BY embedding <=> %(v)s LIMIT %(k)s",
        {"v": vec, "t": space_type, "k": k, "x": exclude, "p": published_only},
    ).fetchall()


def similar_to(relative_path: str, k: int = 6, published_only: bool = False):
    """Same space_type only, so a bedroom never returns a kitchen (seq-2 rule). Unknown path -> []."""
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        row = conn.execute("SELECT embedding, space_type FROM space WHERE relative_path=%s", (relative_path,)).fetchone()
        return _query(conn, row[0], row[1], k, exclude=relative_path, published_only=published_only) if row else []


def by_text(text: str, space_type: str | None = None, k: int = 6, published_only: bool = False):
    vec = np.asarray(_embedder().embed_text(text), dtype=np.float32)
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        return _query(conn, vec, space_type, k, published_only=published_only)


if __name__ == "__main__":
    for r in by_text(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(f"{r[3]:.3f}  {r[0]}  {r[1]}  {r[2]}")
