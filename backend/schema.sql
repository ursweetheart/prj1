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
  nguon_tao text,               -- 'ai' (trigger-managed) | 'ai_bo_sung' (back-tag of an accepted new dimension) | 'nguoi'
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

-- ── Discovery signals and staging (change: discover-taxonomy-dimensions, tasks 1.2-2.2) ──
-- Chat questions the assistant could not answer (act-4 b8): question, folded words no taxonomy synonym covers,
-- best cosine against the knowledge base / photo descriptions. Recurring gaps feed pipeline/discovery.py.
CREATE TABLE IF NOT EXISTS khoang_trong_tri_thuc (
  id serial PRIMARY KEY,
  cau_hoi text NOT NULL,
  tu_chua_khop text[] NOT NULL DEFAULT '{}',
  diem_cao_nhat real,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Behaviour (act-7, NFR-09, NĐ13/2023): a session row exists only once the visitor consented; its id is a random
-- browser token, no account or IP. Without consent only the daily count in su_kien_an_danh moves.
CREATE TABLE IF NOT EXISTS phien_truy_cap (
  id text PRIMARY KEY,
  da_dong_y_thu_thap boolean NOT NULL CHECK (da_dong_y_thu_thap),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS su_kien (
  id serial PRIMARY KEY,
  phien_id text NOT NULL REFERENCES phien_truy_cap(id) ON DELETE CASCADE,
  loai text NOT NULL CHECK (loai IN ('xem_khong_gian')),
  space_id int REFERENCES space(id) ON DELETE SET NULL,
  gia_tri text[] NOT NULL DEFAULT '{}',  -- 'dimension:value' of the viewed space at that moment (facet co-occurrence)
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS su_kien_an_danh (
  ngay date NOT NULL,
  loai text NOT NULL,
  so_luong int NOT NULL DEFAULT 0,
  PRIMARY KEY (ngay, loai)
);

-- 'cho_bang_chung': scored below the promotion threshold, kept until more evidence arrives (never shown for review)
ALTER TABLE ung_vien_phan_loai DROP CONSTRAINT IF EXISTS ung_vien_phan_loai_trang_thai_check;
ALTER TABLE ung_vien_phan_loai ADD CONSTRAINT ung_vien_phan_loai_trang_thai_check
  CHECK (trang_thai IN ('cho_bang_chung', 'cho_duyet', 'chap_nhan', 'tu_choi'));
ALTER TABLE ung_vien_phan_loai ADD COLUMN IF NOT EXISTS updated_at timestamptz;

-- ── Lead intake (change: lead-intake) — one table for every source (dfd-2-4, class-6 KhachTiemNang) ──────────
-- nguon: form | chat | brief | estimate. ho_so_hanh_vi = tom_tat_so_thich: a snapshot of the consented session's views,
-- taken at intake and never recomputed. phien_id is kept only when the visitor also ticked "send what I viewed".
ALTER TABLE lead ADD COLUMN IF NOT EXISTS nguon text;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS ho_ten text;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS so_dien_thoai text;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS loi_nhan text;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS ngu_canh jsonb;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS ho_so_hanh_vi jsonb;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS phien_id text REFERENCES phien_truy_cap(id) ON DELETE SET NULL;
ALTER TABLE lead ALTER COLUMN intent DROP NOT NULL;     -- only chat leads have an intent
UPDATE lead SET nguon = 'chat' WHERE nguon IS NULL;     -- every lead before this change came from the chat
ALTER TABLE lead ALTER COLUMN nguon SET DEFAULT 'form';
ALTER TABLE lead ALTER COLUMN nguon SET NOT NULL;
ALTER TABLE lead DROP CONSTRAINT IF EXISTS lead_nguon_check;
ALTER TABLE lead ADD CONSTRAINT lead_nguon_check CHECK (nguon IN ('form', 'chat', 'brief', 'estimate'));

-- ── Saved collections and design briefs (change: saved-collection-brief; class-6 BoSuuTap, seq-13, seq-7) ─────
-- 'dang_luu': the account's working collection (one per user). 'da_gui': the frozen copy a brief sent, with a share
-- code; nguoi_dung_id is NULL when an anonymous visitor sent it. Anonymous working collections live in the browser.
CREATE TABLE IF NOT EXISTS bo_suu_tap (
  id serial PRIMARY KEY,
  nguoi_dung_id int REFERENCES app_user(id) ON DELETE CASCADE,
  loai text NOT NULL DEFAULT 'dang_luu' CHECK (loai IN ('dang_luu', 'da_gui')),
  ma_chia_se text UNIQUE,
  tom_tat jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((loai = 'da_gui') = (ma_chia_se IS NOT NULL)),
  CHECK (loai = 'da_gui' OR nguoi_dung_id IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS bo_suu_tap_mot_dang_luu ON bo_suu_tap (nguoi_dung_id) WHERE loai = 'dang_luu';
CREATE TABLE IF NOT EXISTS bo_suu_tap_anh (
  bo_suu_tap_id int NOT NULL REFERENCES bo_suu_tap(id) ON DELETE CASCADE,
  space_id int NOT NULL REFERENCES space(id) ON DELETE CASCADE,
  ghi_chu text CHECK (length(ghi_chu) <= 300),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (bo_suu_tap_id, space_id)
);
ALTER TABLE lead ADD COLUMN IF NOT EXISTS bo_suu_tap_id int REFERENCES bo_suu_tap(id) ON DELETE SET NULL;

-- ── Price table D8 for the cost estimate (change: cost-estimate; seq-9, act-6) ─────────────────────────────────
-- One VND/m² range per building type x cost item x package. D3 has no price list yet: the seed below is SAMPLE data
-- (nguon='mau', shown as "Đơn giá mẫu" everywhere). Staff replace it at /quan-tri/don-gia, which sets nguon='d3';
-- ON CONFLICT DO NOTHING means re-applying this file never overwrites an edited row.
CREATE TABLE IF NOT EXISTS don_gia (
  id serial PRIMARY KEY,
  loai_nha text NOT NULL CHECK (loai_nha IN ('can_ho', 'nha_pho', 'biet_thu', 'van_phong', 'thuong_mai')),
  hang_muc text NOT NULL CHECK (hang_muc IN ('thiet_ke', 'phan_tho', 'hoan_thien', 'noi_that')),
  goi text NOT NULL CHECK (goi IN ('co_ban', 'tieu_chuan', 'cao_cap')),
  gia_min bigint NOT NULL,
  gia_max bigint NOT NULL,
  nguon text NOT NULL DEFAULT 'mau' CHECK (nguon IN ('mau', 'd3')),
  ghi_chu text,
  cap_nhat_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
  UNIQUE (loai_nha, hang_muc, goi),
  CHECK (0 <= gia_min AND gia_min <= gia_max)
);
INSERT INTO don_gia (loai_nha, hang_muc, goi, gia_min, gia_max, nguon)
SELECT t.loai_nha, b.hang_muc, b.goi, round(b.lo * t.k * 1000000), round(b.hi * t.k * 1000000), 'mau'
FROM (VALUES  -- apartment base, million VND / m²
  ('thiet_ke',   'co_ban', 0.15, 0.2), ('thiet_ke',   'tieu_chuan', 0.2, 0.3), ('thiet_ke',   'cao_cap', 0.3, 0.45),
  ('phan_tho',   'co_ban', 0.8,  1.2), ('phan_tho',   'tieu_chuan', 1.2, 1.8), ('phan_tho',   'cao_cap', 1.8, 2.5),
  ('hoan_thien', 'co_ban', 1.5,  2.2), ('hoan_thien', 'tieu_chuan', 2.2, 3.5), ('hoan_thien', 'cao_cap', 3.5, 5.5),
  ('noi_that',   'co_ban', 2.0,  3.0), ('noi_that',   'tieu_chuan', 3.0, 5.0), ('noi_that',   'cao_cap', 5.0, 9.0)
) AS b(hang_muc, goi, lo, hi)
CROSS JOIN (VALUES ('can_ho', 1.0), ('nha_pho', 1.1), ('biet_thu', 1.3), ('van_phong', 0.9), ('thuong_mai', 1.15))
  AS t(loai_nha, k)
ON CONFLICT (loai_nha, hang_muc, goi) DO NOTHING;
