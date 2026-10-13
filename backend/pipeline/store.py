"""Persist SpaceRecord + CLIP embedding into Postgres/pgvector (table `space`)."""

import os
import psycopg
from pgvector.psycopg import register_vector
from pipeline.schemas import SpaceRecord

DSN = os.getenv("D3_DSN", "postgresql://d3:d3@localhost:5432/d3")

UPSERT = """
INSERT INTO space (relative_path, image_name, subfolder, space_type, design_style,
  style_confidence, materials, caption, alt_text, palette, hotspots, embedding)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
ON CONFLICT (relative_path) DO UPDATE SET
  space_type=EXCLUDED.space_type, design_style=EXCLUDED.design_style,
  style_confidence=EXCLUDED.style_confidence, materials=EXCLUDED.materials,
  caption=EXCLUDED.caption, alt_text=EXCLUDED.alt_text, palette=EXCLUDED.palette,
  hotspots=EXCLUDED.hotspots, embedding=EXCLUDED.embedding
"""  # review_status deliberately not updated: keep architect's decision on re-ingest


def save_records(records: list[SpaceRecord]) -> int:
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        for r in records:
            c = r.classification
            conn.execute(UPSERT, (
                r.relative_path, r.image_name, r.subfolder,
                c.space_type if c else None, c.design_style if c else None,
                c.design_style_confidence if c else None, c.materials if c else None,
                c.seo_metadata.caption if c else None, c.seo_metadata.alt_text if c else None,
                r.color_analysis.model_dump_json(), r.furniture_detection.model_dump_json(),
                r.embedding,
            ))
    return len(records)
