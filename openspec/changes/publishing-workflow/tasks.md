## 1. Schema

- [ ] 1.1 In `schema.sql`: `space.ngay_xuat_ban`, `kich_thuoc`, `chieu_rong`, `chieu_cao`; `space_text.mo_hinh`; the queue's `loai` CHECK gains `nap_tri_thuc`. Backfill `ngay_xuat_ban` from the last `advance` to `published` in `review_log`.

## 2. Status machine

- [ ] 2.1 Backend (design 1, 2, 4):
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
- [ ] 2.2 Frontend: `NEXT_STATUS` / `STATUS_VI` / `RETURNABLE`, `canEditText`, the "Thiếu: …" message, "Đăng ngày …" on the card.

## 3. Notifications

- [ ] 3.1 `notify.notify_handover` (design 3), called after advances to `editing` and `in_review`. Tests: one email per recipient per action listing every photo; locked accounts skipped; works with email off.

## 4. Assistant knowledge

- [ ] 4.1 `nap_tri_thuc` task handler (design 5), queued on publish; the `space_text` row deleted on take-down; the backfill command. Tests:
  - the composed text holds the labels and no price;
  - publish queues the task;
  - the handler writes the text and embedding with a mocked embedder;
  - take-down removes the row.

## 5. Image sizes

- [ ] 5.1 `pipeline/image_sizes.py` (design 6), called after processing, plus `--backfill`. Tests: widths only below the original, EXIF rotation respected, files served under `/images/_kt/...`.
- [ ] 5.2 `imageSrcset` in `src/api.js`; `SpaceTile.vue` and the ReviewView thumbnails use it. Add a vitest test for `imageSrcset`.

## 6. Verification

- [ ] 6.1 On Docker:
  - run the backfills;
  - in the browser, an architect sends a draft (missing style → message; filled → "Chờ biên tập");
  - a content account edits and sends to review;
  - the lead architect publishes and the publish date shows;
  - the assistant answers with that photo;
  - at 360 px the explorer loads the 480 px copies (network check).

  Full `pytest` and `npm test` green.
