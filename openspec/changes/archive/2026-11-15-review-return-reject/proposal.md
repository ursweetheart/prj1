# Proposal

## Why

The photo review flow (QT-01) only moves forward: draft → in review → approved → rights cleared → published. Two branches in the diagrams have no counterpart in the system.

- **Expert review can reject** (seq-6 steps 9–12). The lead architect enters a reason, the photo goes back to draft, the reason is logged, and the architect is told.
- **The client can refuse publishing** (act-1). The photo is then "Lưu nội bộ, không xuất bản": kept, but never published.

Today a lead architect who disagrees with a label or caption can only leave the photo where it is, or fix it themselves. A refusal from the client has nowhere to go, so the photo waits in "Đã duyệt" forever and can be published by mistake. This is roadmap item 1.8.

## What Changes

- **"Trả về nháp" (return to draft)** from "Chờ duyệt", "Đã duyệt" or "Đã xác nhận quyền", with a required reason of 5–500 characters.
  - Lead architect and admin only.
  - Single photos, or the selection that the bulk bar already supports.
- **"Lưu nội bộ" (keep internal)**, a new final status `noi_bo`, from "Đã duyệt" or "Đã xác nhận quyền", with a required reason (for example "Khách không đồng ý công bố").
  - The photo is never shown publicly and cannot be advanced.
  - "Mở lại" (reopen) sends it back to draft, with a reason.
- **The reason stays with the photo.**
  - It is stored in the review log with who and when.
  - It is also shown on the photo's card in the review queue ("Bị trả về: …" or "Lưu nội bộ: …").
  - The shown reason clears once the photo is advanced again. The log keeps it.
- **The architect is told.** Whoever uploaded the photo gets an email listing the returned photos and the reasons, when SMTP is configured. Otherwise the notice is a log line. A returned draft also carries a "Bị trả về" mark in the queue, and the "Nháp" view can be narrowed to returned drafts.
- **A "Lưu nội bộ" chip** joins the status chips on `/quan-tri`.
- **Fix:** `/quan-tri` gets the header offset that the other staff pages already have.

## Capabilities

### New Capabilities
- `photo-review`: return to draft and keep internal, with reasons, who may do them, how the reason is shown and logged, and the notice to the uploader. The forward steps of the review flow are not covered by any main spec today. This capability starts with the backward paths and can take the forward ones later.

### Modified Capabilities
None.

## Impact

- **Backend:**
  - `backend/schema.sql`: `space.ly_do_duyet`, the reason shown now, with who gave it and when.
  - `backend/api.py`:
    - a new `POST /spaces/return` covering one or many photos;
    - a new `POST /spaces/keep-internal` and `POST /spaces/reopen`;
    - `_advance` clears the shown reason;
    - `review_status` gains `noi_bo`.
  - `backend/pipeline/notify.py`: `notify_returned()`.
  - New tests in `backend/tests/test_review_return.py`.
- **Frontend:**
  - `src/api.js`: `STATUS_VI` gains `noi_bo`, plus the new calls.
  - `src/views/ReviewView.vue`: return, keep-internal and reopen buttons; a reason dialog; the reason shown on each card; a "Chỉ ảnh bị trả về" filter in Nháp; the header offset.
- **Assumptions recorded here:**
  - Returning always goes to **draft**, as seq-6 says, not to the step before. The architect re-confirms the labels and the photo goes through review again.
  - Only the lead architect and admin return, keep internal or reopen. Content editors do not.
- **Out of scope:**
  - unpublishing a published photo;
  - in-app notifications or a notification inbox;
  - returning to a step other than draft.
