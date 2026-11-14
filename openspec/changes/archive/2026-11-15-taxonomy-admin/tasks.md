# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.

Tests create throw-away dimensions and values, and remove them afterwards, so the real taxonomy is not changed.

## 1. Backend

- [x] 1.1 Add the `nhat_ky_phan_loai` table to `backend/schema.sql` and re-apply the schema. Create `pipeline/taxonomy_admin.py` with `slug`, `tree`, `usage`, `add_dimension`, `edit_dimension` (name, visibility, up/down) and `add_value` / `edit_value` (name, description, synonyms normalised), each writing its log row.

  Verify with tests:
  - "Địa Trung Hải" → `dia_trung_hai`;
  - a case-insensitive duplicate is refused;
  - synonyms "  Gỗ Sồi , gỗ sồi" are stored as `["gỗ sồi"]`;
  - a rename keeps the code;
  - moving up swaps with the neighbour, and ties are renumbered;
  - every action writes one log row with its before and after;
  - `usage` counts spaces, published spaces and projects.
- [x] 1.2 Fix the merge in `taxonomy_admin.merge`. Return 422 for a cross-dimension merge or a `tong_mau` merge. Move `space.design_style` / `space_type` for `phong_cach` / `khong_gian` before deleting the source, then move the remaining tags and log the merge.

  Verify with tests on throw-away values of the real `phong_cach` (a temporary value code on throw-away spaces):
  - after the merge the spaces' `design_style` is the target and they carry the target tag;
  - an `UPDATE space SET caption=…` keeps the tag;
  - cross-dimension and `tong_mau` merges give 422;
  - nothing changes after a refused merge.
- [x] 1.3 Add or extend the endpoints:
  - `GET /taxonomy/admin`;
  - `POST /taxonomy`;
  - `PATCH /taxonomy/{dim_id}`;
  - `POST /taxonomy/{dim_id}/values`, where `ma_dinh_danh` is now optional;
  - `PATCH /taxonomy/values/{id}`, which now also takes the description and synonyms;
  - the merge, through the module.

  Each write calls `taxonomy.reload()`.

  Verify with API tests:
  - approver 200/201;
  - sales 403, anonymous 401;
  - the public `GET /taxonomy` reflects a hidden flag and a new value;
  - a new synonym is understood by the assistant's request parsing right after the PATCH;
  - the existing `tests/test_taxonomy*.py` still pass.

## 2. Frontend

- [x] 2.1 In `src/api.js`, add `getTaxonomyAdmin`, `addDimension`, `editDimension`, `addValue`, `editValue` and `mergeValue`. Move the candidate review unchanged into `src/components/TaxonomyCandidates.vue`. Make `TaxonomyView.vue` a two-tab page ("Danh mục" first, `?tab=de-xuat`), with the `page-top` offset.

  Verify in the browser: both tabs work, the arrow keys switch tabs, and the candidate tab still lists the proposals.
- [x] 2.2 Create `src/components/TaxonomyTree.vue`:
  - dimension cards, with a visibility toggle, ↑/↓ and rename;
  - value rows, with name, code, synonyms, usage, "Sửa" and "Gộp vào…" (no merge for `tong_mau`);
  - an add-value form with a code preview, and an add-dimension form;
  - the merge dialog, with the warning and a confirmation;
  - "Gần đây" (the last 20 changes);
  - errors shown next to the field.

  Verify in the browser as a lead architect on throw-away data:
  - add a value and see it in the public filters;
  - rename, and the code is unchanged;
  - edit synonyms;
  - the merge dialog shows the counts, and the merge applies only after "Gộp";
  - hide a dimension, and it disappears from `/khong-gian`;
  - reorder;
  - add a dimension;
  - the log lists each change;
  - 360px has no sideways scroll;
  - keyboard only works.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - UC15 / seq-15 status;
  - roadmap 1.1;
  - the API table;
  - the new table;
  - the merge rule.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
