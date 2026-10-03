CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS space (
  id serial PRIMARY KEY,
  relative_path text UNIQUE NOT NULL,
  image_name text,
  subfolder text,
  space_type text,
  design_style text,
  style_confidence real,
  materials text[],
  caption text,
  alt_text text,
  palette jsonb,
  hotspots jsonb,
  review_status text NOT NULL DEFAULT 'draft',
  embedding vector(768)  -- SigLIP2 ViT-B/16; re-run reembed.py if the embedder changes
);
