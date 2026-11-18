# Design

## Context

- **Upload today:** `POST /spaces/ingest` (`api.py`) takes one file, runs `SpaceImageProcessor.process_image` synchronously (Gemini, palette, YOLO, SigLIP2; "GPU is a single resource"), upserts through `store.save_records`, and returns the space. `src/api.js` `uploadAll` loops over the files one request at a time, and `ReviewView.vue` shows "AI đã xử lý n/N".
- **Classifier:** `SpaceClassificationResult` has `design_style_confidence` only. `store.save_records` writes `style_confidence`.
- **Corrections:** `PATCH /spaces/{id}` writes `review_log` action `edit` with from / to. `eval_labels.py` reconstructs the AI label from the first edit's `from`.
- **Other writers of labels:**
  - `relabel.py` (drafts only);
  - `value_suggest.accept` / `map_to`, which set `design_style` / `space_type` from `Khac`;
  - `sync_projects.ingest`, which calls the processor directly.
- **Schedulers:** background work already runs in the FastAPI lifespan (weekly loop), and it is disabled under pytest.

## Goals / Non-Goals

**Goals:** seq-1 as drawn (queue, immediate answer, done notice, confidence shown, corrections recorded), one photo processed at a time, and nothing lost on restart.

**Non-Goals:**
- Retraining or fine-tuning a model from corrections: seq-1 records them "để đánh giá mô hình", for evaluation only.
- A separate queue service (Redis or Celery). Postgres is enough for one worker at this volume.
- Push notifications: the page polls.

## Decisions

### 1. Queue table and worker

- **Table:**

  ```
  hang_doi_tac_vu(id serial, loai CHECK IN ('xu_ly_anh', ...), du_lieu jsonb, trang_thai CHECK IN ('cho','dang_xu_ly','xong','loi'),
                  so_lan int default 0, space_id int REFERENCES space ON DELETE SET NULL, loi text, nguoi_id, tao_luc,
                  bat_dau_luc, xong_luc)
  ```
- **Worker:** one thread started in the lifespan (not under pytest; `D3_INTAKE_WORKER=off` disables it). Each step:
  1. Claim one task: `UPDATE ... SET trang_thai='dang_xu_ly', so_lan=so_lan+1, bat_dau_luc=now() WHERE id = (SELECT id FROM hang_doi_tac_vu WHERE trang_thai='cho' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING ...`.
  2. Process it with the same `_processor()` and `save_records`.
  3. Write `review_log` `ingest` with the uploader.
  4. Set `xong` and the `space_id`.
- **Idle:** the worker sleeps 2 s when the queue is empty.
- **Failure:** the task is set to `loi` with the exception message cut to 300 characters.
- **Startup:** tasks left in `dang_xu_ly` with `so_lan < 2` go back to `cho`, and the rest become `loi` ("bị gián đoạn hai lần"), so a poison photo can't loop.
- **Task kinds:** one generic table, so the other queued jobs drawn in the diagrams (seq-6 step 18 loading the assistant's knowledge, seq-15 step 20 refreshing the index after a merge) use the same worker. Each kind has a handler; this change adds `xu_ly_anh` (`du_lieu = {relative_path}`).
- **Tests:** `intake.process_next(conn, processor)` is a pure step that tests drive directly with a fake processor.

### 2. Endpoints

- **`POST /spaces/ingest`**:
  - takes `files: list[UploadFile]` (1–50) and `project`;
  - validates the type and size per file, then saves the file and inserts a `cho` task per valid file;
  - returns 202 `{"tasks": [{id, relative_path, trang_thai: "dang_xu_ly"}], "refused": [{name, ly_do}]}`.

  `trang_thai` is reported as "dang_xu_ly" for both queued and running tasks, as seq-1 step 5 says. A same-name re-upload overwrites the file and is queued again, as today.
- **`GET /spaces/ingest/tasks?ids=1,2,3`** (STAFF, at most 200 ids) returns `[{id, trang_thai, space_id, loi}]`.

### 3. Frontend

`uploadAll(files, project, onProgress)`:
1. Sends one multipart request.
2. Polls the tasks every 2 s until every one is `xong` or `loi`, reporting the number done.
3. Returns `{done, failed}`.

`ReviewView` keeps its `<progress>` and live region, then announces "Đã xử lý xong N ảnh", lists failures and reloads the draft list.

### 4. Confidence and the AI's proposal

- The classifier prompt and schema gain `space_type_confidence`, parsed like the style's. When the answer is "Other", the confidence is 0. The offline heuristic path gives fixed values, as today.
- New `space` columns:
  - `space_type_ai`, `design_style_ai`;
  - `space_type_confidence` (`style_confidence` stays the style's).
- `save_records` writes the AI columns on insert and on re-upload; `relabel.py` updates them for drafts.
- **Backfill:** the AI columns take the first `edit` `from` value in `review_log`, otherwise the current value.
- The review list returns the new fields. `ReviewView` shows "AI: <name> · NN%" under each of the two `TagInput`s, plus the text "AI chưa chắc" under 70%.

### 5. Correction records

- **Table:** `nhan_bi_sua(space_id, chieu CHECK IN ('khong_gian','phong_cach'), ai_gia_tri, do_tin_cay, gia_tri_dung, nguoi_id, luc, PRIMARY KEY (space_id, chieu))`.
- **`pipeline/label_feedback.record(conn, space_id, user_id)`** compares the space's current `space_type` / `design_style` with its AI columns:
  - when a value differs, it upserts the row;
  - when it is equal again, it deletes the row.
- **Called from:** `PATCH /spaces/{id}` after a facet edit, `value_suggest.accept` / `map_to` for each moved space, and `tagProject`, if that ever touches these two columns (it does not today).
- `review_log` stays as the full history. The new table is the evaluation set drawn in seq-1 step 21.

### 6. `eval_labels.py`

- **Population:** spaces with an `advance` in `review_log`, as today.
- **AI label:** the AI columns. **Correct label:** the current value. Corrections are listed from `nhan_bi_sua`.
- **New:** accuracy per confidence band.
- The target and minimum sample are unchanged.

## Risks / Trade-offs

- **[Breaking ingest response]** The only caller is `uploadAll`, changed in the same change, and the tests are updated.
- **[Worker in the web process]** This keeps the "one GPU user" property. If the web process is scaled out, `SKIP LOCKED` still prevents double work.
- **[Backfill guesses the AI label for old photos]** The first edit's `from` is exactly what ingest wrote, and unedited photos never differed.

## Migration Plan

1. Apply `schema.sql`, which includes the backfill, and rebuild the backend image.
2. **Rollback:** revert the code. The old synchronous ingest ignores the new tables, and leftover `cho` tasks can be deleted.
