# Design

## Context

- **Hotspot editor:** `HotspotEditor.vue` (ours) edits `objects` and saves through `PUT /spaces/{id}/hotspots` (`saveHotspots`). Objects carry `hotspot_anchor`, `label_vi`, `nguon_tao` and `confidence`. `FurnitureDetector.detect(path)` (YOLOv8s, local) returns objects with boxes in pixels plus confidence. The processor is loaded once (`_processor()`).
- **Items:** `mon_do` has name, kind, style, material, colour, supplier and notes. `items.py` plus `/items` endpoints; edited in `ItemsView.vue` and the editor's item box.
- **Taxonomy merge:** `taxonomy_admin.merge` moves the tags and the columns, then deletes the source value.
- **Photo descriptions:** `space_text` (assistant knowledge, from publishing-workflow's composed description).
- **Accounts:** `app_user` has no name. `/auth/register`, `/users/invite` and the `/users` list are in `auth.py`.
- **Projects:** the `du_an` details are edited by `PUT /projects/{slug}` (`ProjectDetailsIn`, extra fields forbidden).

## Decisions

### 1. Detection on demand

`POST /spaces/{id}/detect` (STAFF):
1. Run `_processor().detector.detect()` under the same lock the queue worker uses, so the GPU never runs two jobs at once.
2. Convert the boxes to 0..1 by the image size.
3. Name objects with the existing detector-label → Vietnamese map used at ingest.
4. Drop those whose centre lies within 0.05 of an existing hotspot with the same name, or that sit inside the box of a same-named object.
5. Return `[{label_vi, box, anchor, confidence}]`.

The editor shows them with a dashed outline and a "Thêm" action. Accepting pushes a point with `nguon_tao: 'ai'` and `confidence`. Saving is unchanged.

### 2. `khoang_gia`

A column with a 60-character CHECK. Added to the items model in, out and edit, and to the editor's item box and `ItemsView`. The public hotspot payload omits it (its field list is explicit).

### 3. Index refresh after a merge

- `merge` collects the affected space ids before moving the tags.
- After the merge commits, it queues `cap_nhat_chi_muc` with `{space_ids}`.
- The handler re-composes and re-embeds `space_text` for those ids that have a row, using publishing-workflow's composer (labels are read fresh, so the old name disappears).
- The merge response gains `so_anh_cap_nhat`, and `TaxonomyTree` shows the sentence.
- The image embeddings don't hold labels, so they need no refresh. Filters read the tables directly.

### 4. `ho_ten`

- `app_user.ho_ten text CHECK (length <= 100)`.
- Set in `/auth/register` (optional field), `/users/invite` (optional), `PATCH /users/{id}` (admin, new), and `PATCH /auth/me` (self, new; name only).
- Returned by `/auth/me` and `/users`. Used in notify emails instead of the email when present.

### 5. Model names

- `space.mo_hinh_nhung text` (set by `save_records` from `VisionEmbedder.model_name`; backfilled with the current name).
- `space_text.mo_hinh` (publishing-workflow sets it).

### 6. Project attributes

- **Columns:** `du_an.du_an_bat_dong_san text (≤ 120)`, `so_ngay_thi_cong int (> 0)`.
- **Migration:** `so_ngay_thi_cong` is filled from `thoi_gian_thi_cong` when that text is a number of days ("90 ngày"). The text column stays for display, since a page owner may show "3 tháng".
- **Editing:** `ProjectDetailsIn` gains both fields.
- **Derived fields:** computed in the project queries from the spaces: `bool_or(published)`, `bool_and(cleared-or-later among published)` (published implies the rights step passed), `min(ngay_xuat_ban)`.

## Risks / Trade-offs

- **[YOLO names fewer kinds than Gemini]** It's an extra helper; staff still choose.
- **[Detection on CPU takes seconds]** The button shows a busy state, and the call is staff-only and rate-limited (10 per 60 s).
