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

-- Access control (task group 6). Safe to re-run on an existing database.
CREATE TABLE IF NOT EXISTS app_user (
  id serial PRIMARY KEY,
  email text UNIQUE NOT NULL,
  password_hash text,           -- NULL for Google-only accounts
  google_sub text UNIQUE,
  role text NOT NULL DEFAULT 'visitor'
    CHECK (role IN ('visitor','architect','content','sales','lead_architect','admin')),
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE app_user ADD COLUMN IF NOT EXISTS facebook_id text UNIQUE;  -- Facebook-only accounts have a placeholder email

-- Audit trail of review actions; survives user deletion.
CREATE TABLE IF NOT EXISTS review_log (
  id serial PRIMARY KEY,
  space_id int REFERENCES space(id) ON DELETE CASCADE,
  user_id int REFERENCES app_user(id) ON DELETE SET NULL,
  action text NOT NULL,         -- ingest | edit | advance
  detail jsonb,
  at timestamptz NOT NULL DEFAULT now()
);

-- RAG assistant (task group 7). Sample data lives in kb/sample.json.
CREATE TABLE IF NOT EXISTS kb_chunk (
  id serial PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('price','faq','service','project')),
  title text UNIQUE NOT NULL,
  content text NOT NULL,
  embedding vector(768)         -- of title + match phrases (short: the SigLIP2 text tower reads ~64 tokens)
);

CREATE TABLE IF NOT EXISTS lead (
  id serial PRIMARY KEY,
  intent text NOT NULL,         -- price | appointment | handoff
  request jsonb,
  conversation jsonb,
  contact text,
  status text NOT NULL DEFAULT 'new',
  created_at timestamptz NOT NULL DEFAULT now()
);
