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

-- ── Trend dashboard (change: trend-dashboard; act-3, seq-4) ────────────────────────────────────────────────
-- Saves join views as consented behaviour signals. 'demo-' sessions come only from pipeline/demo_activity.py.
-- (the allowed su_kien.loai list is set once, in the style-quiz section below, so re-applying never narrows it)
CREATE INDEX IF NOT EXISTS su_kien_created_at ON su_kien (created_at);
CREATE INDEX IF NOT EXISTS bo_suu_tap_loai_created_at ON bo_suu_tap (loai, created_at);

-- ── Style quiz (change: style-quiz; UC06, seq-12) ──────────────────────────────────────────────────────────
-- A quiz answer is a consented behaviour event too; the interest score does not count it (trends.py reads views/saves).
ALTER TABLE su_kien DROP CONSTRAINT IF EXISTS su_kien_loai_check;
ALTER TABLE su_kien ADD CONSTRAINT su_kien_loai_check CHECK (loai IN ('xem_khong_gian', 'luu_anh', 'chon_trac_nghiem',
  'xem_trang', 'xem_du_an', 'bam_CTA', 'gui_form', 'nhan_chatbot', 'chia_se', 'ap_dung_bo_loc'));  -- behaviour-events
-- one saved result per account; re-scored by the server on save, suggestions re-read (unpublished ones dropped)
CREATE TABLE IF NOT EXISTS ket_qua_trac_nghiem (
  nguoi_dung_id int PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
  phong_cach jsonb NOT NULL,        -- [{ma, ten, ti_le}], best first
  goi_y int[] NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ── Taxonomy admin (change: taxonomy-admin; seq-15, UC15) ─────────────────────────────────────────────────
-- Every staff edit of the taxonomy: who, what, before -> after (them_chieu | sua_chieu | them_gia_tri | sua_gia_tri | gop_gia_tri).
CREATE TABLE IF NOT EXISTS nhat_ky_phan_loai (
  id serial PRIMARY KEY,
  nguoi_dung_id int REFERENCES app_user(id) ON DELETE SET NULL,
  hanh_dong text NOT NULL,
  doi_tuong text NOT NULL,          -- 'phong_cach' or 'phong_cach:Japandi'
  truoc jsonb,
  sau jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS nhat_ky_phan_loai_created_at ON nhat_ky_phan_loai (created_at DESC);

-- ── Review: return to draft / keep internal (change: review-return-reject; act-1, seq-6) ────────────────
-- review_status also takes 'noi_bo' (kept internal, never published). ly_do_duyet = the reason shown on the card now:
-- {loai: tra_ve | noi_bo | mo_lai, ly_do, boi (email), luc}; cleared when the photo is advanced. review_log keeps all.
ALTER TABLE space ADD COLUMN IF NOT EXISTS ly_do_duyet jsonb;

-- ── Assistant knowledge admin (change: assistant-knowledge-admin; UC16, seq-16) ──────────────────────────
-- An entry is used by the chatbot only while 'dang_dung'. cum_tu_khop = the match phrases embedded with the title
-- (stored now, so an edit can re-embed). nguon: mau (sample) | ai (AI draft) | nhan_vien (staff) | tep (file).
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS cum_tu_khop text NOT NULL DEFAULT '';
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS trang_thai text NOT NULL DEFAULT 'dang_dung';
ALTER TABLE kb_chunk DROP CONSTRAINT IF EXISTS kb_chunk_trang_thai_check;
ALTER TABLE kb_chunk ADD CONSTRAINT kb_chunk_trang_thai_check CHECK (trang_thai IN ('nhap', 'cho_duyet', 'dang_dung', 'tat'));
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS nguon text;
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS tu_cau_hoi int[] NOT NULL DEFAULT '{}';  -- unanswered questions it was written from
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS updated_by int REFERENCES app_user(id) ON DELETE SET NULL;
UPDATE kb_chunk SET cum_tu_khop = title WHERE cum_tu_khop = '';
UPDATE kb_chunk SET nguon = CASE WHEN content LIKE '[DỮ LIỆU MẪU]%' THEN 'mau' WHEN content LIKE '[AI SINH%' THEN 'ai' ELSE 'tep' END
  WHERE nguon IS NULL;
-- unanswered questions: open until an entry answers them (da_xu_ly) or staff dismiss them (bo_qua)
ALTER TABLE khoang_trong_tri_thuc ADD COLUMN IF NOT EXISTS trang_thai text NOT NULL DEFAULT 'mo';
ALTER TABLE khoang_trong_tri_thuc DROP CONSTRAINT IF EXISTS khoang_trong_tri_thuc_trang_thai_check;
ALTER TABLE khoang_trong_tri_thuc ADD CONSTRAINT khoang_trong_tri_thuc_trang_thai_check CHECK (trang_thai IN ('mo', 'da_xu_ly', 'bo_qua'));
ALTER TABLE khoang_trong_tri_thuc ADD COLUMN IF NOT EXISTS kb_chunk_id int REFERENCES kb_chunk(id) ON DELETE SET NULL;
CREATE TABLE IF NOT EXISTS nhat_ky_tri_thuc (
  id serial PRIMARY KEY,
  kb_chunk_id int,                  -- kept after a delete (no FK), so the log still says what was removed
  nguoi_dung_id int REFERENCES app_user(id) ON DELETE SET NULL,
  hanh_dong text NOT NULL,          -- tao | sua | trang_thai | xoa | bo_qua_cau_hoi
  truoc jsonb,
  sau jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ── Account admin (change: user-admin; UC24, seq-19 b16-19) ─────────────────────────────────────────────
-- bi_khoa: cannot sign in. phien_tu: tokens issued (iat) before it are refused, which is how a lock ends open sessions.
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS bi_khoa boolean NOT NULL DEFAULT false;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS ly_do_khoa text;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS phien_tu timestamptz;
CREATE TABLE IF NOT EXISTS nhat_ky_tai_khoan (
  id serial PRIMARY KEY,
  nguoi_dung_id int REFERENCES app_user(id) ON DELETE SET NULL,     -- the admin (NULL: set_role.py)
  tai_khoan_id int REFERENCES app_user(id) ON DELETE CASCADE,       -- the account changed
  hanh_dong text NOT NULL,                                          -- doi_vai_tro | khoa | mo_khoa
  truoc jsonb,
  sau jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Weekly report (change weekly-report; UC23, seq-18). One row per week, claimed before sending so a restart never sends twice.
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS nhan_bao_cao_tuan boolean NOT NULL DEFAULT true;
CREATE TABLE IF NOT EXISTS bao_cao_tuan (
  tuan_bat_dau date PRIMARY KEY,  -- the Monday (UTC+7) of the week reported
  gui_luc timestamptz NOT NULL DEFAULT now(),
  so_nguoi_nhan int NOT NULL DEFAULT 0,
  so_loi int NOT NULL DEFAULT 0,
  ket_qua text NOT NULL DEFAULT 'dang_gui'
    CHECK (ket_qua IN ('dang_gui', 'da_gui', 'loi_mot_phan', 'loi', 'chi_ghi_log')),
  tieu_de text,
  noi_dung text
);

-- Chat conversations (change chat-history; seq-3 b18, class-4 HoiThoai / TinNhan). Kept anonymously 90 days after the
-- last message; linked to a session only when it exists in phien_truy_cap (= the visitor accepted collection).
-- Phone numbers and emails in visitor messages are masked before storing.
CREATE TABLE IF NOT EXISTS hoi_thoai (
  id text PRIMARY KEY,                -- 32 hex chars, random: holding it is what lets a visitor read or delete it
  phien_id text REFERENCES phien_truy_cap(id) ON DELETE SET NULL,
  rang_buoc jsonb NOT NULL DEFAULT '{}',   -- project_type, space_type, area_m2, design_style collected so far
  da_chuyen_nguoi_that boolean NOT NULL DEFAULT false,
  bat_dau timestamptz NOT NULL DEFAULT now(),
  cap_nhat timestamptz NOT NULL DEFAULT now(),
  so_tin_nhan int NOT NULL DEFAULT 0,
  chua_tra_loi int NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS hoi_thoai_cap_nhat ON hoi_thoai (cap_nhat DESC);
CREATE TABLE IF NOT EXISTS tin_nhan (
  id serial PRIMARY KEY,
  hoi_thoai_id text NOT NULL REFERENCES hoi_thoai(id) ON DELETE CASCADE,
  vai_tro text NOT NULL CHECK (vai_tro IN ('khach', 'tro_ly')),
  noi_dung text NOT NULL,
  nguon jsonb,
  diem_cao_nhat real,
  tra_loi_duoc boolean,
  thoi_diem timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tin_nhan_hoi_thoai ON tin_nhan (hoi_thoai_id, id);
ALTER TABLE lead ADD COLUMN IF NOT EXISTS hoi_thoai_id text REFERENCES hoi_thoai(id) ON DELETE SET NULL;

-- Item library for hotspots (change hotspot-items; seq-14, class-1 MonDo). Hotspots stay in space.hotspots.objects;
-- an object may carry nguon_tao ('ai' | 'thu_cong') and mon_do_id. Supplier and note are never sent to visitors.
CREATE TABLE IF NOT EXISTS mon_do (
  id serial PRIMARY KEY,
  ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 120),
  ten_khoa text NOT NULL UNIQUE,      -- folded name: the duplicate check (case and accents ignored)
  phan_loai text CHECK (length(phan_loai) <= 60),
  kieu_dang text CHECK (length(kieu_dang) <= 60),
  vat_lieu text CHECK (length(vat_lieu) <= 60),
  mau_sac text CHECK (length(mau_sac) <= 40),
  nha_cung_cap text CHECK (length(nha_cung_cap) <= 120),
  ghi_chu text CHECK (length(ghi_chu) <= 500),
  tao_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  cap_nhat_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Behaviour events (change behaviour-events; UC21, class-4 SuKien): page / project views with time and scroll, CTA clicks,
-- forms, chat, share, filters. Pages are stored as route patterns (/bo-suu-tap/xem/:ma), never the real path or query.
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS trang text;
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS doi_tuong text;
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS thoi_gian_dung_ms int;
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS do_sau_cuon real;

-- Password links (change account-invites-reset; UC24, seq-19 b7-11): invitation (72 h) and reset (1 h) links, single use.
-- Only a sha256 of the random code is stored; issuing a link voids the account's earlier active links.
CREATE TABLE IF NOT EXISTS ma_dat_mat_khau (
  id serial PRIMARY KEY,
  tai_khoan_id int NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  loai text NOT NULL CHECK (loai IN ('moi', 'dat_lai')),
  ma_bam text NOT NULL UNIQUE,
  het_han timestamptz NOT NULL,
  da_dung timestamptz,
  da_huy timestamptz,
  tao_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ma_dat_mat_khau_tai_khoan ON ma_dat_mat_khau (tai_khoan_id);

-- Forbidden topics (change topic-guard-sitemap-item-services; seq-3 b15): keywords the assistant must not discuss.
-- A question or answer that hits a switched-on topic is replaced by the handoff message; the hit is kept on the reply.
CREATE TABLE IF NOT EXISTS chu_de_cam (
  id serial PRIMARY KEY,
  ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 80),
  ten_khoa text NOT NULL UNIQUE,      -- folded name: the duplicate check (case and accents ignored)
  tu_khoa text[] NOT NULL CHECK (cardinality(tu_khoa) BETWEEN 1 AND 30),
  ghi_chu text CHECK (length(ghi_chu) <= 300),
  bat boolean NOT NULL DEFAULT true,
  tao_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  cap_nhat_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE tin_nhan ADD COLUMN IF NOT EXISTS chu_de_cam jsonb;  -- {id, ten, o: cau_hoi | tra_loi}; staff only

-- Item -> service package (same change; roadmap 1.9): the visitor's hotspot card shows it, over the label mapping.
ALTER TABLE mon_do ADD COLUMN IF NOT EXISTS dich_vu_id int REFERENCES kb_chunk(id) ON DELETE SET NULL;

-- review-tag-autocomplete: a reviewer's suggested new value (loai = 'gia_tri') waits here with the photos set to "Other"
-- until an approver decides. bang_chung = {chieu, khoa (folded text), space_ids, nguoi_de_xuat, mo_ta, tu_dong_nghia, ai}.
-- One undecided suggestion per dimension and folded word, so two reviewers typing the same word share it.
CREATE UNIQUE INDEX IF NOT EXISTS ung_vien_gia_tri_mot_tu ON ung_vien_phan_loai ((bang_chung->>'chieu'), (bang_chung->>'khoa'))
  WHERE loai = 'gia_tri' AND trang_thai = 'cho_duyet';

-- project-catalog (roadmap 0.1): one record per project, shared by the site, the AI backend and the dashboards.
-- Site fields (ten..co_trang) come from src/data/projects.js via sync_projects.py; the details are staff-entered.
CREATE TABLE IF NOT EXISTS du_an (
  slug text PRIMARY KEY CHECK (slug ~ '^[a-z0-9-]{1,60}$'),
  ten text NOT NULL,
  loai text,
  nam int,
  mo_ta_ngan text,
  thu_tu int,                       -- position in the site's list; NULL = folder-only project
  co_trang boolean NOT NULL DEFAULT false,  -- has a /du-an/<slug> page
  dien_tich_m2 numeric CHECK (dien_tich_m2 > 0),
  so_phong_ngu int CHECK (so_phong_ngu > 0),
  thoi_gian_thi_cong text CHECK (length(thoi_gian_thi_cong) <= 80),
  muc_dau_tu text,                  -- a muc_dau_tu taxonomy value
  thuyet_minh text CHECK (length(thuyet_minh) <= 4000),
  cap_nhat_luc timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS nhat_ky_du_an (
  id serial PRIMARY KEY,
  du_an_slug text REFERENCES du_an(slug) ON UPDATE CASCADE ON DELETE CASCADE,
  user_id int REFERENCES app_user(id) ON DELETE SET NULL,  -- NULL = the sync
  hanh_dong text NOT NULL,          -- lien_ket | sua | nhung (site-photo embedding cache)
  chi_tiet jsonb,
  luc timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE space ADD COLUMN IF NOT EXISTS du_an_slug text REFERENCES du_an(slug) ON UPDATE CASCADE ON DELETE SET NULL;
ALTER TABLE space ADD COLUMN IF NOT EXISTS anh_trang text;  -- the site file it matches, e.g. 02.jpg
CREATE INDEX IF NOT EXISTS space_du_an ON space (du_an_slug);

-- labelling-queue-feedback (seq-1): uploads go through a task queue; a single worker runs one task at a time.
-- loai names the handler (pipeline/intake.py HANDLERS): xu_ly_anh = process an uploaded photo (du_lieu.relative_path).
CREATE TABLE IF NOT EXISTS hang_doi_tac_vu (
  id serial PRIMARY KEY,
  loai text NOT NULL,
  du_lieu jsonb NOT NULL DEFAULT '{}',
  trang_thai text NOT NULL DEFAULT 'cho' CHECK (trang_thai IN ('cho', 'dang_xu_ly', 'xong', 'loi')),
  so_lan int NOT NULL DEFAULT 0,
  space_id int REFERENCES space(id) ON DELETE SET NULL,
  loi text,
  nguoi_id int REFERENCES app_user(id) ON DELETE SET NULL,
  tao_luc timestamptz NOT NULL DEFAULT now(),
  bat_dau_luc timestamptz,
  xong_luc timestamptz
);
CREATE INDEX IF NOT EXISTS hang_doi_tac_vu_cho ON hang_doi_tac_vu (id) WHERE trang_thai = 'cho';
-- what the AI proposed, kept unchanged by human edits (seq-1 b11): the evaluation baseline
ALTER TABLE space ADD COLUMN IF NOT EXISTS space_type_ai text;
ALTER TABLE space ADD COLUMN IF NOT EXISTS design_style_ai text;
ALTER TABLE space ADD COLUMN IF NOT EXISTS space_type_confidence real;
-- backfill once: the AI label is the 'from' side of the first human edit, else the current label
UPDATE space s SET
  space_type_ai = COALESCE((SELECT r.detail->'from'->>'space_type' FROM review_log r WHERE r.space_id = s.id
                            AND r.action = 'edit' AND r.detail->'from' ? 'space_type' ORDER BY r.id LIMIT 1), s.space_type),
  design_style_ai = COALESCE((SELECT r.detail->'from'->>'design_style' FROM review_log r WHERE r.space_id = s.id
                              AND r.action = 'edit' AND r.detail->'from' ? 'design_style' ORDER BY r.id LIMIT 1), s.design_style)
WHERE s.space_type_ai IS NULL AND s.design_style_ai IS NULL;
-- seq-1 b21: one row per photo and dimension while the saved label differs from the AI's
CREATE TABLE IF NOT EXISTS nhan_bi_sua (
  space_id int NOT NULL REFERENCES space(id) ON DELETE CASCADE,
  chieu text NOT NULL CHECK (chieu IN ('khong_gian', 'phong_cach')),
  ai_gia_tri text,
  do_tin_cay real,
  gia_tri_dung text,
  nguoi_id int REFERENCES app_user(id) ON DELETE SET NULL,
  luc timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (space_id, chieu)
);
-- backfill: corrections made before nhan_bi_sua existed (idempotent: only photos with no row yet)
INSERT INTO nhan_bi_sua (space_id, chieu, ai_gia_tri, do_tin_cay, gia_tri_dung)
SELECT id, 'khong_gian', space_type_ai, space_type_confidence, space_type FROM space
 WHERE space_type_ai IS NOT NULL AND space_type IS DISTINCT FROM space_type_ai
UNION ALL
SELECT id, 'phong_cach', design_style_ai, style_confidence, design_style FROM space
 WHERE design_style_ai IS NOT NULL AND design_style IS DISTINCT FROM design_style_ai
ON CONFLICT (space_id, chieu) DO NOTHING;
