# Design

## Context

- **Status machine:** `api.py` has `NEXT = {draft: in_review, in_review: approved, approved: cleared, cleared: published}`. `_advance` lets STAFF move a draft and only APPROVERS move the rest. `RETURNABLE = {in_review, approved, cleared}`. `review_status` is free text, with no CHECK constraint.
- **Frontend:** `src/api.js` mirrors the machine (`NEXT_STATUS`, `STATUS_VI`, `RETURNABLE`). `ReviewView` lets content editors edit text only when the status is `in_review`.
- **Email:** `pipeline/notify.py` has `_send` and `_smtp_ready`, and already notifies uploaders on returns.
- **Dimensions:** `chieu_phan_loai.bat_buoc` marks required dimensions. Room type and style live in `space` columns; the other dimensions live in `space_gia_tri`.
- **Assistant photo knowledge:** `space_text(space_id, transcript, embedding)` is read by `assistant.retrieve_photos` (Vertex `text-embedding`, `RETRIEVAL_DOCUMENT`). It is written only by `generate_transcripts.py` (Gemini) and holds 0 rows.
- **Images:** served from `/images/<relative_path>` (StaticFiles over `image_d3`), built by `imageUrl()` in `src/api.js`.

## Decisions

### 1. Status `editing`

- `NEXT` becomes `draft → editing → in_review → approved → cleared → published`. `_advance` role rules:
  - draft: STAFF;
  - editing: `content` + APPROVERS;
  - the rest: APPROVERS.
- `RETURNABLE` gains `editing`.
- Content may PATCH caption and alt text when the status is `editing`. `in_review` keeps working for photos already there, so nothing needs migrating.
- Frontend: `NEXT_STATUS`, `STATUS_VI.editing = 'Chờ biên tập'`, and `RETURNABLE` updated; `canEditText` becomes `content && status in (editing, in_review)`; ReviewView's status tabs come from `STATUS_VI`, so the new tab appears.

### 2. Required dimensions

`_missing_required(c, space_id)` checks every `chieu_phan_loai` with `bat_buoc`:
- for `khong_gian` / `phong_cach`, the photo's column is non-empty;
- for the others, at least one `space_gia_tri` row exists in that dimension.

It is checked in `_advance` when the status is `draft`, and fails with 422 `{"thieu": [names]}`. ReviewView shows "Thiếu: …" on the card when the API answers that.

### 3. Notifications

New functions in `notify.py`:
- `notify_handover(kind, items, by)`, where `kind` is `bien_tap` (to `content`) or `duyet` (to `lead_architect`);
- recipients are unlocked accounts of that role;
- one email per recipient per action, sent as a BackgroundTask after the advance commits.

### 4. Publish date

`space.ngay_xuat_ban timestamptz` is set in `_advance` when the new status is `published`. Reopen and take-down leave it as it was until the next publish overwrites it. It is returned in `FIELDS`.

### 5. Assistant knowledge on publish

- **Queue:** a `nap_tri_thuc` task kind in the queue (`labelling-queue-feedback`), `du_lieu = {space_id}`.
- **Handler:**
  1. Compose a Vietnamese transcript from the caption, value names of all dimensions, materials, palette names and item names. No price words: the existing `FORBIDDEN` filter is applied.
  2. Embed it with `vertex.embed([...], "RETRIEVAL_DOCUMENT")`.
  3. Upsert `space_text`, plus `mo_hinh` (the embedding model's name; class-6 VectorMoTa `ten_mo_hinh`).
- **When:** queued after the advance to `published`. Take-down (`unpublish`) deletes the `space_text` row in the same transaction.
- **Existing photos:** a backfill command queues the already-published photos once.

### 6. Image sizes (`pipeline/image_sizes.py`)

- `make(path) -> {"kich_thuoc": {"480": "...", ...}, "chieu_rong", "chieu_cao"}`.
- **How:** Pillow, `ImageOps.exif_transpose`, `thumbnail` to each width (only widths smaller than the original), WebP quality 80. Files are written to `image_d3/_kt/<width>/<relative_path>.webp`, so the existing `/images` mount serves them.
- **Columns:** `space.kich_thuoc jsonb`, `chieu_rong int`, `chieu_cao int`.
- **When:** called by the intake handler after `save_records`. `python -m pipeline.image_sizes --backfill` covers existing photos.
- **Frontend:** `imageSrcset(space)` in `src/api.js` builds the attribute. `SpaceTile.vue` and ReviewView's thumbnails use `srcset` and `sizes`. Tùng's views keep their own `<img>`; this is a known limit.

## Risks / Trade-offs

- **[Extra step slows publishing]** It is what QT-01 draws, and an approver can still move editing → review alone when no content editor exists.
- **[Disk]** The copies add about 30% to the image folder. That's acceptable at this size.
- **[Composed descriptions are plainer than Gemini's]** They are built only from reviewed data, cost nothing, and `generate_transcripts.py --redo` can still write richer ones.

## Migration Plan

1. Apply `schema.sql`.
2. Run the image backfill, then queue knowledge loading for the published photos.
3. **Rollback:** photos in `editing` would be unknown to the old code. Move them back first with `UPDATE space SET review_status='draft' WHERE review_status='editing'`.
