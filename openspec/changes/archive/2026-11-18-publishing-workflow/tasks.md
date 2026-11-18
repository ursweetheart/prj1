## 1. Schema

- [x] 1.1 In `schema.sql`: `space.ngay_xuat_ban`, `kich_thuoc`, `chieu_rong`, `chieu_cao`; `space_text.mo_hinh`; the queue's `loai` CHECK gains `nap_tri_thuc`. Backfill `ngay_xuat_ban` from the last `advance` to `published` in `review_log`.

## 2. Status machine

- [x] 2.1 Backend (design 1, 2, 4):
  - `NEXT` with `editing` and the `_advance` role rules;
  - the required-dimension check with 422 `thieu`;
  - `RETURNABLE` + `editing`;
  - content PATCH allowed in `editing`;
  - `ngay_xuat_ban` on publish;
  - `FIELDS`.

  Tests:
  - the full chain by role;
  - an architect gets 403 on editing;
  - a missing required dimension gives 422 with its name;
  - return from editing;
  - the publish date is set.

  Update the existing review tests.
- [x] 2.2 Frontend: `NEXT_STATUS` / `STATUS_VI` / `RETURNABLE`, `canEditText`, the "Thiếu: …" message, "Đăng ngày …" on the card.

## 3. Notifications

- [x] 3.1 `notify.notify_handover` (design 3), called after advances to `editing` and `in_review`. Tests: one email per recipient per action listing every photo; locked accounts skipped; works with email off.

## 4. Assistant knowledge

- [x] 4.1 `nap_tri_thuc` task handler (design 5), queued on publish; the `space_text` row deleted on take-down; the backfill command. Tests:
  - the composed text holds the labels and no price;
  - publish queues the task;
  - the handler writes the text and embedding with a mocked embedder;
  - take-down removes the row.

## 5. Image sizes

- [x] 5.1 `pipeline/image_sizes.py` (design 6), called after processing, plus `--backfill`. Tests: widths only below the original, EXIF rotation respected, files served under `/images/_kt/...`.
- [x] 5.2 `imageSrcset` in `src/api.js`; `SpaceTile.vue` and the ReviewView thumbnails use it. Add a vitest test for `imageSrcset`.

## 6. Verification

- [x] 6.1 On Docker:
  - run the backfills;
  - in the browser, an architect sends a draft (missing style → message; filled → "Chờ biên tập");
  - a content account edits and sends to review;
  - the lead architect publishes and the publish date shows;
  - the assistant answers with that photo;
  - at 360 px the explorer loads the 480 px copies (network check).

  Full `pytest` and `npm test` green.

## Results (2026-11-18)

- **Note on the task list:** the queue's `loai` has no CHECK (handlers are registered in `pipeline/intake.py`), so 1.1's "CHECK gains `nap_tri_thuc`" became registering its handler (`pipeline/space_knowledge.py`).
- **Backfills:**
  - `ngay_xuat_ban` set for all 40 published photos;
  - copies made for 186 photos in about 1 min (50 MB against 2.5 GB of originals);
  - knowledge loaded for the 40 published photos through the queue. `space_text` held 0 rows before, so the assistant's photo search had nothing to search; now "phòng ngủ Indochine gỗ sẫm" returns the right photos (0.90).
- **Fixes found while checking:**
  - `.webp` was served as octet-stream (MIME type registered);
  - Vue set `src` before `srcset`, so every original was downloaded too (attributes reordered);
  - descriptions were joined with double periods.
- **Browser, headless:**
  - a draft without a style showed "Thiếu: Phong cách" on its card and stayed a draft; with the style it went to "Chờ biên tập";
  - the content account edited the caption and sent it to "Chờ duyệt";
  - the lead approved, cleared and published it, and the card showed "Đăng ngày 18/11/2026";
  - its description was in the assistant's knowledge within seconds;
  - at 360 px the explorer loaded only 480 px copies;
  - the photo was restored afterwards.
- **Tests:** `pytest` 505 passed (3 known environment failures; `test_photo_rag` passes now); `npm test` 83 passed.
