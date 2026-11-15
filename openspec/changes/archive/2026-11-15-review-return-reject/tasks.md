# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.

Tests use throw-away spaces (`test_rr_*/`) and throw-away accounts, removed afterwards.

## 1. Backend

- [x] 1.1 Add `ALTER TABLE space ADD COLUMN IF NOT EXISTS ly_do_duyet jsonb` to `backend/schema.sql` and re-apply it. In `backend/api.py`, add `_move_back` and the three endpoints `POST /spaces/return`, `/spaces/keep-internal` and `/spaces/reopen` (approvers; body `{space_ids, ly_do}`; all or nothing). Make `_advance` clear `ly_do_duyet`. Have staff `GET /spaces` return `ly_do_duyet` and accept `tra_ve=1`.

  Verify with tests in `tests/test_review_return.py`:
  - returning from in_review, approved and cleared lands in draft, with the reason and who and when;
  - published, draft and noi_bo are refused with 409, and a mixed selection moves nothing;
  - a reason of fewer than 5 characters gives 422;
  - an architect or content editor gets 403, and anonymous 401;
  - keep-internal from approved works, then advancing gives 409;
  - reopen goes to draft;
  - advancing again clears `ly_do_duyet`, and `review_log` still has the reason;
  - `tra_ve=1` lists only returned drafts;
  - `GET /spaces/{id}` gives 404 for a noi_bo photo to a visitor, and the public `GET /spaces` never includes `ly_do_duyet`;
  - `tests/test_review_workflow.py` still passes, apart from its known data failure.
- [x] 1.2 Add `notify.notify_returned(items)`, called as a background task after each of the three endpoints. It finds the uploader from the latest `ingest` log row, groups by uploader, sends one email per uploader through SMTP or writes a log line otherwise, and never raises.

  Verify with tests:
  - two photos from one uploader produce one message naming both reasons (capture `_send` or the log);
  - a photo without an uploader only logs;
  - a failing `_send` does not change the response.

## 2. Frontend

- [x] 2.1 In `src/api.js`, add `STATUS_VI.noi_bo` and the calls `returnSpaces`, `keepInternal` and `reopenSpaces`. In `ReviewView.vue`:
  - the card buttons for approvers;
  - the bulk "Trả về nháp N mục";
  - the reason dialog (labelled textarea, counter, error under the field, Esc and focus return);
  - the reason block on cards;
  - "Chỉ ảnh bị trả về" in Nháp;
  - `page-top`.

  Verify in the browser as a lead architect on throw-away photos:
  - return one photo, and it shows in Nháp with the reason;
  - bulk return two photos;
  - a short reason shows the error and sends nothing;
  - keep one internal, and it appears under "Lưu nội bộ" with no advance button, and is 404 on its public page;
  - reopen it;
  - the filter shows only returned drafts;
  - advance a returned draft, and the reason disappears;
  - an architect account sees no return buttons;
  - keyboard only works;
  - no sideways scroll at 360px;
  - the title is not under the header.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - roadmap 1.8;
  - the seq-6 / act-1 status;
  - the API table;
  - the column;
  - the new `noi_bo` status in the status list.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
