# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.
- **Throw-away data:** tests use throw-away photos (`test_up_*`), a test item, collection and brief, all removed afterwards. The browser check uses throw-away photos too, so no real published photo is ever taken down.

## 1. Backend

- [x] 1.1 Add `BACK` entries `unpublish` (published → draft, `go_xuong`) and `unpublish_internal` (published → noi_bo, `go_noi_bo`), and `POST /spaces/unpublish {space_ids, ly_do, giu_noi_bo}` for APPROVERS. Add `go_xuong` to the `tra_ve=1` filter and both kinds to `notify.KIND_VI`.

  Verify with API tests:
  - taking a photo down to draft and to internal moves it, sets `ly_do_duyet`, and writes a review_log row with `from: published`;
  - a mixed selection gives 409 naming the non-published photo, and nothing moves;
  - a reason of 4 characters gives 422;
  - architect and content get 403, and anonymous 401;
  - `/spaces/return` on a published photo still gives 409;
  - `notify_returned` logs "Gỡ khỏi website" with the reason (SMTP unset);
  - a draft taken down appears under `tra_ve=1`;
  - an internal one can be reopened.
- [x] 1.2 The public-trace test, as in the design. Before the take-down the photo is listed by:
  - the visitor's `/spaces/{id}`;
  - `/spaces`;
  - `/search` (text);
  - `/projects/{folder}/spaces`;
  - `/items/{id}/spaces`;
  - `project_stats.overview`;
  - the saved collection;
  - the sent copy.
  
  After it, it is in none of them, and `/spaces/{id}` gives 404 for a visitor. After publishing again, it is back in the saved list and the sent copy.

## 2. Frontend

- [x] 2.1 `src/api.js`: add `unpublishSpaces(ids, lyDo, giuNoiBo)`. `ReviewView.vue`:
  - "Gỡ khỏi website" per card and in bulk on the "Đã đăng" tab, for approvers;
  - the dialog's outcome choice (radio group, labelled);
  - `REASON_VI` and the card colours for the two new kinds.

  Verify in the browser as the lead architect, on two throw-away published photos:
  - one taken down "để sửa" shows under "Nháp" with "Đã gỡ khỏi website: …" and under "Chỉ ảnh bị trả về";
  - the other taken down "lưu nội bộ" shows under "Lưu nội bộ" with its reason;
  - the visitor `/khong-gian/<id>` of each shows "not found";
  - the dialog works by keyboard (arrows switch the outcome, Esc cancels and focus returns);
  - an architect sees no take-down button;
  - no sideways scroll at 360px with the dialog open.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - UC14 (unpublishing done);
  - roadmap 1.8's remaining item;
  - act-1;
  - the API table;
  - a known issue for raw image files reachable by URL;
  - the fixing list.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
