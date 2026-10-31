## 1. Bulk project upload

- [x] 1.1 `POST /spaces/ingest` takes form field `project`; `project_folder()` folds it to `[a-z0-9_]`, empty → `uploads/`; unit test for folding and path escape
- [x] 1.2 `src/api.js`: `ingestSpace(file, project)` (multipart)
- [x] 1.3 Review page: multi-file picker + project name, sequential sends, progress `n/N`, per-file error list, reload the `Nháp` tab when done

## 2. Edit AI content and the content role

- [x] 2.1 `Review` model + `PATCH /spaces/{id}`: `caption`, `alt_text`, `materials`; log changed fields with before/after
- [x] 2.2 Allow `content` on `PATCH`: only `caption` / `alt_text`, only `in_review`, else 403
- [x] 2.3 pytest: text/material edit re-tags `vat_lieu`; content-role allowed and refused cases
- [x] 2.4 Review page: caption / alt / materials fields; `content` sees only the text fields in `Chờ duyệt`

## 3. Cleared state and bulk advance

- [x] 3.1 `NEXT` gains `cleared`; `approved → cleared` requires `rights_confirmed` (422) and an approver; log the flag
- [x] 3.2 Shared advance helper; `POST /spaces/advance` `{space_ids, rights_confirmed}` in one transaction, failure names the space and rolls back
- [x] 3.3 pytest: full order through `cleared`, missing confirmation, architect refused, bulk success and bulk rollback
- [x] 3.4 `src/api.js` `NEXT_STATUS` / `STATUS_VI` (`Đã xác nhận quyền`); review page: row selection, "chọn cả dự án", rights checkbox, bulk advance, hide actions the role cannot use

## 4. Human tags

- [x] 4.1 `PUT /spaces/tags` `{space_ids | project, dimension, values}`: replace `nguoi` rows; 422 for AI-mirrored dimensions, unknown values, multiple values on a single-value dimension
- [x] 4.2 pytest: tag a project, replace, refusals
- [x] 4.3 Review page: `loai_cong_trinh` and `muc_dau_tu` selects (values from `/taxonomy`) with "Áp cho cả dự án"

## 5. Hotspot confirmation

- [x] 5.1 `PATCH /spaces/{id}` `hotspots: [{index, label_vi}]` keep-list; 422 on unknown index; logged
- [x] 5.2 pytest: remove + rename keeps the anchor; bad index refused
- [x] 5.3 Review page: detected objects listed on the image, remove / rename, save
- [x] 5.4 Space detail page shows the kept hotspots on the image (`HotspotImage`, until now used by nothing), so a removed object disappears publicly

## 6. Verification

- [x] 6.1 Full backend suite and `npx vitest run` pass; `npm run build` succeeds
- [ ] 6.2 Walk one real project through upload → edit → tags → approve → cleared → published in the browser and see it filtered on `/cong-trinh` by `loai_cong_trinh`
