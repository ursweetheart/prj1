# Design

## Context

- **Endpoints today** (`api.py`):
  - `GET /taxonomy` (public, used by the filters);
  - `POST /taxonomy/{dim_id}/values`, which takes `ma_dinh_danh` from the client;
  - `PATCH /taxonomy/values/{id}` (name only);
  - `POST /taxonomy/values/{id}/merge`;
  - the candidate endpoints.

  All writes call `taxonomy.reload()`, which drops the `lru_cache` that the assistant and the classifier read.
- **The `sync_ai_tags` trigger** rebuilds a space's `nguon_tao='ai'` tags from `space_type`, `design_style`, `palette` and `materials` on every write to those columns. Human tags (`nguon_tao='nguoi'`) and back-tags (`ai_bo_sung`) are left alone.
- **Codes in use** mix case: `Hien_dai`, `Wabi_sabi` and `Khac` in `phong_cach`, but lower case elsewhere. `project_folder()` folds a name to lower case.
- **The current page** `TaxonomyView.vue` is the candidate review (109 lines).
- **Existing pages** use `.txt`, `.panel`, `.btn` and the `page-top` header offset.

## Goals / Non-Goals

**Goals:** every seq-15 path (add value, rename, merge with warning), plus synonyms and dimension editing, from the browser; merges that leave the mirrored columns consistent; an audit trail.

**Non-Goals:**
- deleting values or dimensions;
- bulk edits;
- undo;
- telling the AI classifier about a new dimension. A manual dimension is tagged by people, or by accepting an AI proposal.

## Decisions

### 1. One module, thin endpoints
`pipeline/taxonomy_admin.py` holds the SQL and rules. Each function takes a connection and the user, writes the change and its log row in that same transaction, and returns the new row:
- `tree(conn)`
- `add_dimension(conn, user, ten, nhieu, hien_thi)`
- `edit_dimension(conn, user, dim_id, ten?, hien_thi?, move?)`
- `add_value(conn, user, dim_id, ten, mo_ta, syn)`
- `edit_value(conn, user, value_id, ten?, mo_ta?, syn?)`
- `merge(conn, user, src, dst)`

The endpoints in `api.py` map `ValueError` subclasses to 404, 409 and 422, and call `taxonomy.reload()` after commit.

### 2. Codes derived on the server
The server derives a new value's or dimension's code with the same fold as `project_folder` (`slug()` moves into `taxonomy_admin` and `project_folder` calls it).
- **Collision check:** case-insensitive within the dimension, so "japandi" collides with `Japandi`.
- **Preview:** the UI shows the code with a client-side copy of the fold. The server's answer is the one that counts.
- **The existing POST:** `POST /taxonomy/{dim_id}/values` keeps accepting `ma_dinh_danh` for compatibility, but the new UI sends only `ten`. When the code is omitted, it is derived.

### 3. Merge rules
These checks run in one transaction:
- **404** when either value is missing.
- **422** when the two values are in different dimensions, or the dimension is `tong_mau`. `DERIVED = {"tong_mau"}`; its values are the palette's brightness and temperature words.
- **Mirrored columns:** if the dimension is in `MIRRORED = {"phong_cach": "design_style", "khong_gian": "space_type"}`, run `UPDATE space SET <col> = target_code WHERE <col> = source_code`. This runs before the source value is deleted. The trigger then re-tags those spaces with the target, and the `nguon_tao='ai'` rows follow.
- **Remaining tags:** the existing tag move (skipping spaces that already carry the target), then delete the source.
- **Log:** `{nguon, dich, so_khong_gian, so_du_an}`.

The warning numbers come from `usage(conn, value_id)`, which counts tagged spaces and distinct project folders (the first path segment of `relative_path`). The tree carries the same numbers, so the confirm dialog needs no extra call.

- *Alternative: leave the columns and only move tags.* This is the current bug: the trigger and the quiz read the columns.

### 4. Synonyms
`tu_dong_nghia` is stored trimmed, in lower case, deduplicated, at most 30 entries of up to 60 characters each. Accents are kept. The UI edits them as one comma-separated field.

There are two readers:
- **Material tagging** (the `sync_ai_tags` trigger) compares them **with** accents against material text such as "gỗ óc chó".
- **Request parsing** compares them with the folded (accent-free) message.

Today the seeded synonyms of the parsed dimensions happen to be stored folded ("phong khach"). So `taxonomy.synonym_map()` now folds its keys, and a synonym typed with accents ("bắc âu") is matched too. The fold moves into `taxonomy.py` (`fold()`), and `assistant._fold` uses it.

### 5. Order
`edit_dimension(move='up'|'down')` swaps `thu_tu` with the neighbour in the current order (by `thu_tu, id`). Before swapping, it renumbers all dimensions to 1..n once, so ties never block a move.

### 6. Log table
```sql
nhat_ky_phan_loai (id serial, nguoi_dung_id int REFERENCES app_user ON DELETE SET NULL,
                   hanh_dong text, doi_tuong text, truoc jsonb, sau jsonb, created_at timestamptz DEFAULT now())
```
- `hanh_dong` ∈ `them_chieu`, `sua_chieu`, `them_gia_tri`, `sua_gia_tri`, `gop_gia_tri`.
- `GET /taxonomy/admin` returns `{chieu: [...], gan_day: [20 latest with user email]}`.

### 7. Frontend
- **`TaxonomyView.vue`** becomes a two-tab page (`role="tablist"`, arrow keys switch tabs, `?tab=de-xuat` deep link):
  - "Danh mục" renders `TaxonomyTree.vue`;
  - "Đề xuất của AI" renders the current candidate UI, moved to `TaxonomyCandidates.vue` unchanged.
- **`TaxonomyTree.vue`:**
  - one card per dimension: name, code, a "Hiện cho khách" toggle, ↑ / ↓, "Đổi tên";
  - inside each card, a value table that becomes a list on phones (name, code, synonyms, "n không gian · m đã đăng"), with "Sửa" and "Gộp vào…" per row;
  - an "Thêm giá trị" form at the bottom of each card, and a "Thêm chiều" form at the end.
- **Edits** open inline. "Gộp vào…" opens a `<dialog>` with a `<select>` of the other values in the dimension, the warning sentence, and "Gộp" / "Huỷ". `tong_mau` shows no merge button.
- **After each save** the tree reloads from `GET /taxonomy/admin`, so the counts and the log are always the server's.

## Risks / Trade-offs

- **[A merge rewrites many spaces at once]** With today's data that is at most a few dozen rows. → One transaction, so it either happens completely or not at all. The trigger runs once per space.
- **[Mixed-case codes]** A new value gets a lower-case code beside `Hien_dai`-style ones. → The collision check is case-insensitive. The codes are internal: visitors see names.
- **[Hiding a dimension the AI fills]** For example `phong_cach`: the tags keep being written and the trend dashboard skips it. → Allowed; the toggle's help text says what hiding does.
- **[The classifier does not learn new values]** `pipeline/schemas.py` still lists the space types and styles as fixed `Literal`s for Gemini's structured output (existing debt, against data-driven-taxonomy). → A value added here is used by staff tagging (`PUT /spaces/tags`), the filters, the assistant's parsing and material synonyms right away. The AI keeps proposing only the fixed codes until that schema is built from the taxonomy (follow-up, noted in TONG-QUAN-DU-AN.md).

## Migration Plan

- `schema.sql` adds `nhat_ky_phan_loai` (idempotent). Re-apply it, then rebuild backend and web.
- No data migration.
- **Rollback:** the old endpoints keep their shape. The only behaviour change is that the merge now refuses cross-dimension and `tong_mau` merges, and moves the mirrored columns.
