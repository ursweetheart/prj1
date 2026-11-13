"""Similarity search over `space` (seq-2). python -m pipeline.search "warm wood bedroom" [space_type]"""

import sys
from collections import Counter
from functools import lru_cache
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from pipeline.store import DSN

COLS = "relative_path, space_type, design_style, 1 - (embedding <=> %(v)s) AS score, id"
WHERE = ("WHERE (%(t)s::text IS NULL OR space_type = %(t)s) AND (%(x)s::text IS NULL OR relative_path <> %(x)s) "
         "AND (NOT %(p)s OR review_status = 'published')")


MAX_K = 24
# photo search, measured on the 152-space library (spike in search-by-image/design.md):
MIN_IMAGE_SCORE = 0.65  # interiors not in the library scored 0.70-0.92; the logo 0.595, noise 0.53, flat grey 0.58
DUP_SCORE = 0.99        # stored duplicate photos score 1.0; a cropped JPEG q60 copy of one photo 0.89-0.97
PER_PROJECT = 2         # unlimited, top-5 was often five shots of one project


@lru_cache(maxsize=1)
def _embedder():  # load the model once per process, not per query
    from pipeline.vision_embedder import VisionEmbedder
    return VisionEmbedder()


def _query(conn, vec, space_type, k, exclude=None, published_only=False):
    k = max(1, min(k, MAX_K))
    return conn.execute(
        f"SELECT {COLS} FROM space {WHERE} ORDER BY embedding <=> %(v)s LIMIT %(k)s",
        {"v": vec, "t": space_type, "k": k, "x": exclude, "p": published_only},
    ).fetchall()


def similar_to(relative_path: str, k: int = 6, published_only: bool = False):
    """Same space_type only, so a bedroom never returns a kitchen (seq-2 rule). Unknown path -> []."""
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        row = conn.execute("SELECT embedding, space_type FROM space WHERE relative_path=%s", (relative_path,)).fetchone()
        return _query(conn, row[0], row[1], k, exclude=relative_path, published_only=published_only) if row else []


def by_text(text: str, space_type: str | None = None, k: int = 6, published_only: bool = False):
    """Rows like _query's, at most PER_PROJECT per project so one project's shots don't fill the page."""
    k = max(1, min(k, MAX_K))
    vec = np.asarray(_embedder().embed_text(text), dtype=np.float32)
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        rows = conn.execute(f"SELECT {COLS}, subfolder FROM space {WHERE} ORDER BY embedding <=> %(v)s LIMIT %(n)s",
                            {"v": vec, "t": space_type, "x": None, "p": published_only, "n": 4 * MAX_K}).fetchall()
    kept, per = [], Counter()
    for r in rows:  # best first
        if per[r[5]] < PER_PROJECT:
            kept.append(r[:5])
            per[r[5]] += 1
            if len(kept) == k:
                break
    return kept


def by_image(fp, space_type: str | None = None, k: int = 6, published_only: bool = False):
    """fp: path or file object; the photo is only embedded, never stored. Rows like _query's, minus
    weak matches, near-duplicates of a better hit, and a project's shots beyond PER_PROJECT."""
    k = max(1, min(k, MAX_K))
    vec = np.asarray(_embedder().embed_image(fp), dtype=np.float32)  # decode errors (OSError) propagate
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        rows = conn.execute(f"SELECT {COLS}, subfolder, embedding FROM space {WHERE} ORDER BY embedding <=> %(v)s LIMIT %(n)s",
                            {"v": vec, "t": space_type, "x": None, "p": published_only, "n": 4 * MAX_K}).fetchall()
    kept, embs, per = [], [], Counter()
    for r in rows:  # best first
        if r[3] < MIN_IMAGE_SCORE or len(kept) == k:
            break
        e = r[6].to_numpy()
        if per[r[5]] >= PER_PROJECT or any(np.dot(e, x) >= DUP_SCORE for x in embs):  # embeddings are unit-length
            continue
        kept.append(r[:5])
        embs.append(e)
        per[r[5]] += 1
    return kept


if __name__ == "__main__":
    for r in by_text(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(f"{r[3]:.3f}  {r[0]}  {r[1]}  {r[2]}")
