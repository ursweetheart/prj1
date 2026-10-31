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

-- Long-form description of each photo (Gemini) and its text embedding (Vertex text-multilingual-embedding-002), for chat RAG.
CREATE TABLE IF NOT EXISTS space_text (
  space_id int PRIMARY KEY REFERENCES space(id) ON DELETE CASCADE,
  transcript text NOT NULL,
  embedding vector(768),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ── Data-driven taxonomy (change: discover-taxonomy-dimensions) ───────────────
-- Replaces the Literal enums in pipeline/schemas.py and the synonym dicts in
-- pipeline/assistant.py. ma_dinh_danh is the STABLE id used in facet URLs (NFR-07);
-- ten is the editable label, so a rename changes ten only and never breaks a URL.
CREATE TABLE IF NOT EXISTS chieu_phan_loai (
  id serial PRIMARY KEY,
  ma_dinh_danh text UNIQUE NOT NULL,
  ten text NOT NULL,
  bat_buoc boolean NOT NULL DEFAULT false,
  cho_phep_nhieu_gia_tri boolean NOT NULL DEFAULT false,
  hien_thi_cho_khach boolean NOT NULL DEFAULT true,
  thu_tu int NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gia_tri_phan_loai (
  id serial PRIMARY KEY,
  chieu_id int NOT NULL REFERENCES chieu_phan_loai(id) ON DELETE CASCADE,
  ma_dinh_danh text NOT NULL,
  ten text NOT NULL,
  mo_ta text,
  tu_dong_nghia jsonb NOT NULL DEFAULT '[]',  -- customer vocabulary -> this value (seeds parse_request)
  anh_minh_hoa text,
  UNIQUE (chieu_id, ma_dinh_danh)
);

-- Space is the unit of tagging (M1): a space carries values across many dimensions.
CREATE TABLE IF NOT EXISTS space_gia_tri (
  space_id int NOT NULL REFERENCES space(id) ON DELETE CASCADE,
  gia_tri_id int NOT NULL REFERENCES gia_tri_phan_loai(id) ON DELETE CASCADE,
  do_tin_cay real,              -- tagging confidence; low ones flagged for review (QT01)
  nguon_tao text,               -- 'ai' | 'nguoi'
  PRIMARY KEY (space_id, gia_tri_id)
);

-- The AI-labelled dimensions mirror the space's own columns, on every write path (ingest, review edit,
-- relabel). Rows with nguon_tao='nguoi' (loai_cong_trinh, muc_dau_tu, manual extras) are never touched.
-- vat_lieu: a synonym matches the leading words of a material ("gỗ" -> "gỗ óc chó", "da" -/-> "đá").
CREATE OR REPLACE FUNCTION sync_ai_tags() RETURNS trigger AS $$
BEGIN
  DELETE FROM space_gia_tri WHERE space_id = NEW.id AND nguon_tao = 'ai';
  INSERT INTO space_gia_tri (space_id, gia_tri_id, do_tin_cay, nguon_tao)
  SELECT NEW.id, v.id, CASE WHEN d.ma_dinh_danh = 'phong_cach' THEN NEW.style_confidence END, 'ai'
  FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id
  WHERE (d.ma_dinh_danh = 'khong_gian' AND v.ma_dinh_danh = NEW.space_type)
     OR (d.ma_dinh_danh = 'phong_cach' AND v.ma_dinh_danh = NEW.design_style)
     OR (d.ma_dinh_danh = 'tong_mau' AND v.ma_dinh_danh IN (NEW.palette->>'brightness', NEW.palette->>'temperature'))
     OR (d.ma_dinh_danh = 'vat_lieu' AND EXISTS (
           SELECT 1 FROM unnest(NEW.materials) m, jsonb_array_elements_text(v.tu_dong_nghia) s
           WHERE lower(m) = s OR lower(m) LIKE s || ' %'))
  ON CONFLICT DO NOTHING;
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER space_ai_tags AFTER INSERT OR UPDATE OF space_type, design_style, palette, materials
  ON space FOR EACH ROW EXECUTE FUNCTION sync_ai_tags();

-- AI-proposed taxonomy changes awaiting human approval; never live until accepted (M9, seq-15).
CREATE TABLE IF NOT EXISTS ung_vien_phan_loai (
  id serial PRIMARY KEY,
  loai text NOT NULL CHECK (loai IN ('chieu','gia_tri','dong_nghia')),  -- dimension | value | synonym
  ten_de_xuat text NOT NULL,
  bang_chung jsonb,             -- variance explained, #images, #chat, #sessions, pole example ids
  trang_thai text NOT NULL DEFAULT 'cho_duyet' CHECK (trang_thai IN ('cho_duyet','chap_nhan','tu_choi')),
  created_at timestamptz NOT NULL DEFAULT now()
);
