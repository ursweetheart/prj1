"""Recompute only the embedding column for every row in `space` (no Gemini calls). Use after changing the embedder."""
import psycopg
from pgvector.psycopg import register_vector
from pipeline.store import DSN
from pipeline.vision_embedder import VisionEmbedder

if __name__ == "__main__":
    emb = VisionEmbedder()
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE space SET embedding = NULL")
        conn.execute("ALTER TABLE space ALTER COLUMN embedding TYPE vector(768)")
        register_vector(conn)
        for (p,) in conn.execute("SELECT relative_path FROM space").fetchall():
            conn.execute("UPDATE space SET embedding=%s WHERE relative_path=%s", (emb.embed_image(f"image_d3/{p}"), p))
    print("done")
