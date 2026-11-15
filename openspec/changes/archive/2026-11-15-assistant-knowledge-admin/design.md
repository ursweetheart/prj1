# Design

## Context

- **The table.** `kb_chunk (id, kind CHECK price|faq|service|project, title UNIQUE, content, embedding vector(768))`. The embedding is the SigLIP2 text tower over `"{title}. {match}"`, but `match` is not stored. So an entry cannot be re-embedded after an edit without the original JSON.
- **Retrieval.** `assistant.retrieve()` takes the top 3 by cosine over all rows. `respond()` answers with the top entry's text when its score is ≥ `MIN_SCORE` (0.88), and returns the text as is, including any "[DỮ LIỆU MẪU]" prefix.
- **Loading.** `assistant.load_kb(path)` validates the file and upserts by title. It warns about markers but loads everything as live.
- **Hotspot links.** `assistant.SERVICE_BY_LABEL` maps detected objects to 3 service titles, and `with_services()` adds those titles to hotspots. Renaming such a title breaks the link silently.
- **Unanswered questions.** `khoang_trong_tri_thuc (id, cau_hoi, tu_chua_khop[], diem_cao_nhat, created_at)` is written by `_log_gap` for every unanswered question. There are 15 rows, nothing reads them except `discovery.py`, and nothing closes them.
- **Data today:** 11 live entries, all marked "[DỮ LIỆU MẪU]". `kb/generated.json` has 8 project drafts marked "[AI SINH - CHƯA DUYỆT]" that were never loaded.
- **Roles:** `EDITORS = STAFF + content`; `APPROVERS = lead_architect, admin`. Content staff are `content`.

## Goals / Non-Goals

**Goals:**
- seq-16 end to end: unanswered questions → draft → approval for prices → switched on and embedded → questions closed;
- editing without JSON;
- AI drafts never used unreviewed.

**Non-Goals:**
- versions or undo;
- bulk import from the UI (the CLI stays for files);
- editing photo transcripts;
- changing `MIN_SCORE` or the answer logic.

## Decisions

### 1. Store match phrases and status on `kb_chunk`
These columns are added idempotently:
- `cum_tu_khop text NOT NULL DEFAULT ''`;
- `trang_thai text NOT NULL DEFAULT 'dang_dung' CHECK (trang_thai IN ('nhap','cho_duyet','dang_dung','tat'))`;
- `nguon text` (`mau` | `ai` | `nhan_vien` | `tep`);
- `updated_at`;
- `updated_by` (referencing `app_user`).

**Existing rows** keep `dang_dung` through the default, so the chatbot behaves exactly as before. Their `cum_tu_khop` is backfilled from the JSON files where the title matches (sample.json holds the 11 live ones). Any row left over falls back to its title. `nguon` is `mau` when the text has the sample marker.

**Retrieval:** `retrieve()` adds `WHERE trang_thai = 'dang_dung'`.

**The partial index:** the embedding search scans the table. With tens of rows no index is needed.

### 2. One module, `pipeline/knowledge.py`
- **Reads:** `list_entries(conn, q, trang_thai)` and `get(conn, id)`.
- **Writes:** `create`, `update`, `set_status`, `delete`.
- **Questions:** `gaps(conn)`, `dismiss_gap`.
- **Helpers:** `needs_price_approval(kind, content)` and `embed(title, cum_tu_khop)`.

Each write takes the user, runs in the caller's transaction, and logs to `nhat_ky_tri_thuc (id, kb_chunk_id, nguoi_dung_id, hanh_dong, truoc jsonb, sau jsonb, created_at)`.

The embedding is computed before the transaction (it takes about 0.1 s on CPU, and the model is already loaded for chat). It is written together with the row, so a saved entry is never left with an old vector.

### 3. The price rule
```
MONEY = r"\d[\d.,]*\s*(triệu|tr\b|tỷ|nghìn|ngàn|k\b|đ|đồng|vnd|vnđ|usd|\$)|/\s*m(2|²)"
needs_price_approval = kind == 'price' or re.search(MONEY, content, re.I)
```

`set_status(…, 'dang_dung')` by a content user on such an entry answers 403 with "Mục có giá cần KTS trưởng duyệt". The UI shows "Gửi duyệt" instead of "Bật sử dụng" for that case.

`update()` by a content user on a live entry: if the new answer differs and needs price approval, the status becomes `cho_duyet`. If only the title or match phrases changed, it stays live and is re-embedded. An approver's edits never change the status.

Allowed status moves:

| From | To | Who |
| :-- | :-- | :-- |
| nhap | cho_duyet | anyone permitted |
| nhap, cho_duyet, tat | dang_dung | approver, or content when no price approval is needed |
| dang_dung | tat | anyone permitted |
| any | nhap | anyone permitted ("Về nháp") |

### 4. AI drafts
- `load_kb()` stores an entry as `cho_duyet` with `nguon='ai'` when its content starts with the AI marker, and keeps `cum_tu_khop` from the file's `match`.
- An upsert does **not** overwrite the status of an existing row. Re-loading a file never switches off a live entry, and never switches on a draft.
- On a move to `dang_dung`, a leading "[AI SINH - CHƯA DUYỆT] " is stripped and `nguon` becomes `nhan_vien`.
- The sample marker is not stripped automatically. The team removes it by editing the text when the real content is written (roadmap 1.6). The UI shows a "Dữ liệu mẫu" badge while it is there.

### 5. Hotspot-linked titles are protected
`LINKED = set(SERVICE_BY_LABEL.values())`. `update` refuses a title change, and `delete` refuses deletion, for a row whose current title is in `LINKED` (409, "Điểm nóng đang liên kết tới mục này"). Editing its text is fine.

### 6. Unanswered questions
- **New columns:** `khoang_trong_tri_thuc` adds `trang_thai text NOT NULL DEFAULT 'mo' CHECK (… 'mo','da_xu_ly','bo_qua')` and `kb_chunk_id int REFERENCES kb_chunk ON DELETE SET NULL`.
- **Grouping:** `gaps()` groups open rows by `lower(unaccent-like fold)` of the trimmed question, computed in Python with `taxonomy.fold`, because Postgres has no `unaccent` installed. Each group has its ids, the question shown (the most recent wording), the count, the last time asked, and the union of unknown words. It is sorted by count, then by the most recent.
- **"Soạn đáp án"** passes the group's ids to the new-entry form (`tu_cau_hoi: [ids]`). The ids are stored on the draft (`kb_chunk.tu_cau_hoi int[]`). When the entry first becomes `dang_dung`, those rows are set to `da_xu_ly` with `kb_chunk_id`.
- **"Bỏ qua"** sets the group to `bo_qua`.
- **Discovery** (`discovery.py`) keeps reading all rows as before, including closed ones, so its evidence is not lost.

### 7. Endpoints
All take `require("content", *APPROVERS)`, except DELETE, which takes `require(*APPROVERS)`.

| Method | Path | Body or query |
| :-- | :-- | :-- |
| GET | `/knowledge` | `?q=&trang_thai=` |
| GET | `/knowledge/{id}` | |
| POST | `/knowledge` | `{kind, title, cum_tu_khop, content, trang_thai: nhap\|cho_duyet, tu_cau_hoi?}` |
| PATCH | `/knowledge/{id}` | `{kind?, title?, cum_tu_khop?, content?}` |
| POST | `/knowledge/{id}/status` | `{trang_thai}` |
| DELETE | `/knowledge/{id}` | |
| GET | `/knowledge/gaps` | |
| POST | `/knowledge/gaps/dismiss` | `{ids}` |

Errors are mapped as 404, 409 (title taken or linked), 422 (validation) and 403 (price rule). Each list item carries `can_duyet_gia`, `mau` (sample marker present) and `lien_ket` (hotspot-linked), so the UI shows the right buttons.

### 8. Frontend
- **`KnowledgeView.vue`** at `/quan-tri/tri-thuc` (`meta.roles: ['content', ...APPROVERS]`), with two tabs like `/quan-tri/phan-loai`: "Mục tri thức" and "Câu hỏi chưa trả lời (n)".
- **The entries tab:**
  - a search field, status chips with counts, and "+ Mục mới";
  - each row shows the title, kind, status badge, "Dữ liệu mẫu" / "AI soạn" / "Có giá" badges, and the first line of the answer;
  - clicking a row opens an editor panel below it: kind select, title, match phrases with help text, and an answer textarea with a counter;
  - the editor's buttons depend on the role and status: "Lưu", "Gửi duyệt", "Bật sử dụng", "Tắt", "Về nháp", "Xoá" (approvers; a confirm dialog);
  - errors are shown next to the fields.
- **The questions tab:** groups with the question, "×n", last time, unknown words as chips, "Soạn đáp án" (switches to the entries tab with the form pre-filled) and "Bỏ qua".
- **Nav:** `SiteNav` adds `hasRole(['content', ...APPROVERS]) && { to: '/quan-tri/tri-thuc', label: 'Tri thức' }`.
- **The page** uses `page-top`.

## Risks / Trade-offs

- **[The money regex misses or over-matches]** Missing "hai trăm triệu" in words is possible, and so is matching "3 đến 4 tuần". → Over-matching only asks for an approval. The `price` kind is always checked. The regex needs a digit followed by a money unit, so plain durations do not match. Tests cover both.
- **[Embedding on every save]** The first save after a restart loads SigLIP2 (a few seconds). → Same as the first chat; acceptable for staff.
- **[Content waiting on approval]** A live price entry edited by content disappears from answers until approved. → This is the rule in seq-16. The chatbot falls back to the handoff message and the lead is captured.
- **[Grouping in Python]** All open rows are read. → They number in the tens. A `trang_thai` index is enough.

## Migration Plan

- Run `schema.sql` (idempotent):
  - the new columns;
  - the backfill of `cum_tu_khop` from the title;
  - `nguon` from the markers;
  - the new log table.
- Then `docker compose exec backend python -m pipeline.assistant kb/sample.json` restores the real match phrases of the 11 sample entries. The upsert keeps their status.
- Then `… kb/generated.json` loads the 8 drafts as `cho_duyet`.
- **Rollback:** the columns are additive. Old code would read every row, including drafts. Switch drafts off or delete them before rolling back.
