## 1. Schema

- [x] 1.1 In `backend/schema.sql` (idempotent):
  - `hang_doi_tac_vu`;
  - `nhan_bi_sua`;
  - `space` columns `space_type_ai`, `design_style_ai`, `space_type_confidence`;
  - backfill of the AI columns from the first `edit` `from` in `review_log`, otherwise the current value.

  Verify: applying it twice on Docker succeeds, and the backfill matches `eval_labels.py`'s old reconstruction.

## 2. Confidence

- [x] 2.1 Add `space_type_confidence` to the classifier prompt, `SpaceClassificationResult` and its parsing ("Other" gives 0; the offline path gives fixed values). Make `store.save_records` write the AI columns and both confidences, and `relabel.py` refresh them for drafts. Tests: parsing with and without the field, and save writes the AI columns.

## 3. Queue

- [x] 3.1 Create `backend/pipeline/intake.py`:
  - `enqueue`, `process_next` (claim with `SKIP LOCKED`), `recover` (startup rule) and `status`;
  - the worker thread started in the lifespan (off under pytest and with `D3_INTAKE_WORKER=off`).

  Tests with a fake processor:
  - order;
  - failure marks `loi` and the next task still runs;
  - recover retries once, then fails;
  - two concurrent claims never take the same task.
- [x] 3.2 `POST /spaces/ingest` becomes the batch (1–50 files) and answers 202 with tasks and refused files. Add `GET /spaces/ingest/tasks`. Tests:
  - roles (401 / 403);
  - a bad file is refused alone;
  - more than 50 files gives 422;
  - status reports the space id when done.

  Update the existing ingest tests.
- [x] 3.3 `src/api.js` `uploadAll`: one request, then poll every 2 s. In `ReviewView.vue`:
  - progress from the tasks;
  - the "Đã xử lý xong N ảnh" live announcement;
  - the failures list;
  - reload of the drafts.

  Add a vitest test for the polling helper.

## 4. Corrections

- [x] 4.1 Create `backend/pipeline/label_feedback.record` and call it from `PATCH /spaces/{id}` and `value_suggest.accept` / `map_to`. Tests:
  - correction then revert;
  - accept updates the correct value;
  - one row per photo and dimension.
- [x] 4.2 The review list returns the AI columns and confidences. `ReviewView.vue` shows "AI: <name> · NN%" and "AI chưa chắc" under 70%.
- [x] 4.3 `eval_labels.py` reads the AI columns and `nhan_bi_sua`, and adds accuracy per confidence band. Update its test.

## 5. Verification

- [x] 5.1 Browser on Docker as a lead architect:
  - upload 3 photos (and 1 PDF): the answer comes at once with "đang xử lý", progress moves, then "Đã xử lý xong 3 ảnh" and the PDF refused;
  - the cards show the AI proposals with confidence;
  - correct a style: a `nhan_bi_sua` row appears; revert: it disappears;
  - restart the backend mid-queue: the queue resumes.
- [x] 5.2 Run `eval_labels.py` and record the output. Full `pytest` and `npm test` green (apart from the known environment failures). Remove the test data.

## Results (2026-11-18)

- **Browser, headless, as a lead architect:**
  - uploading 3 photos and a PDF answered in 118 ms with 3 tasks "dang_xu_ly" and the PDF refused;
  - the backend was restarted while task 25 was running; it was requeued (`so_lan` 2) and every task finished, with "Đã xử lý xong 3 ảnh" after 84 s;
  - the card showed "Loại không gian AI: Phòng khách · 95% / Phong cách AI: Hiện đại · 90%";
  - changing the style recorded a correction, and changing it back removed it.
- **`eval_labels.py`:** 41 reviewed photos; room type 39/41 = 95%, style 38/41 = 93% (NFR-10 met); 5 corrections listed after the backfill. The per-band numbers fill as new photos come through the queue (older photos have no room-type confidence).
- **Fix found while checking:** the review list now loads every page of 200 rows, so new uploads are never cut off once there are more than 200 photos in a status.
- **Tests:** `pytest` 471 passed, with the 4 known environment failures (GPU, photo-RAG public search, project tagging, search fixture image); `npm test` 73 passed.
