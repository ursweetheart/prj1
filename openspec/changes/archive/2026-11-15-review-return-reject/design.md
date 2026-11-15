# Design

## Context

- **Statuses.** `space.review_status` is free text with no CHECK. `api.NEXT` holds the forward steps. `_advance(c, id, status, user, rights)` checks roles and rights, updates the status and writes `review_log (action='advance', detail={from,to})`.
- **Endpoints.** `PATCH /spaces/{id}` (`advance: true`) and `POST /spaces/advance` (a list, all or nothing, rows locked `FOR UPDATE`) use it.
- **Public reads already filter on `published`:**
  - `GET /spaces` and `/spaces/{id}` (404 otherwise);
  - search with `published_only`;
  - similar spaces;
  - project spaces;
  - the quiz;
  - the trend dashboard's top spaces.

  So a new status is hidden from the public without any change.
- **Who uploaded.** `review_log` has an `ingest` row per photo with `user_id`, which tells us the uploader.
- **Email.** `pipeline/notify.py` sends mail through SMTP when `D3_SMTP_HOST` is set, and otherwise writes a log line on `d3.leads`. It never raises.
- **The page.** `ReviewView.vue` shows status chips from `STATUS_VI`, a bulk bar, and per-photo cards grouped by project. It still uses its own `padding-block`, so its title sits under the fixed header.

## Goals / Non-Goals

**Goals:** the two backward paths of the diagrams, with a reason everyone can see, an audit trail, and a notice to the uploader. No change to the forward flow.

**Non-Goals:**
- unpublishing;
- a notification inbox;
- returning to a step other than draft;
- per-reviewer assignment.

## Decisions

### 1. One helper beside `_advance`
`_move_back(c, id, status, user, to, reason, action)` does four things:
- checks the allowed source statuses (`RETURNABLE = {in_review, approved, cleared}` for a return, `{approved, cleared}` for keep-internal, `{noi_bo}` for reopen);
- sets the status;
- sets the shown reason;
- logs `{from, to, reason}` under `action` = `return`, `keep_internal` or `reopen`.

Three thin endpoints share one body model, `{space_ids: [..1..500], ly_do: str(5..500, trimmed)}`. Each one locks the rows `FOR UPDATE`. A photo in the wrong status makes the whole call 409, naming that photo; an unknown id makes it 404.
- `POST /spaces/return`
- `POST /spaces/keep-internal`
- `POST /spaces/reopen`

The role is `require(*APPROVERS)`.

- *Alternative: extend `PATCH /spaces/{id}` with `return: true`.* It would mix edits and moves, and it covers one photo only. Separate verbs keep each rule obvious.

### 2. The shown reason lives on the space
New columns:
- `space.ly_do_duyet jsonb`: `{loai: 'tra_ve'|'noi_bo'|'mo_lai', ly_do, boi: email, luc}`. Shown on the card, so the queue needs no join on the log.
- Who and when are inside that JSON, so there is no second column.

`_advance` sets `ly_do_duyet = NULL`. `GET /spaces` (staff) returns the field. The public field list is unchanged, so visitors never see the reason. `GET /spaces?tra_ve=1` lists only rows whose `ly_do_duyet->>'loai'` is `tra_ve` or `mo_lai`. It is staff-only, because visitors only ever see published photos.

### 3. Keep internal is a status, not a flag
`review_status = 'noi_bo'`, which is absent from `NEXT`. So `_advance` already answers 409 ("final state") and every public read already excludes it. Reopen sets it back to `draft`.

### 4. Notice to the uploader
After commit, the endpoint starts a `BackgroundTasks` job: `notify.notify_returned(items)`, where items are `[(space_id, relative_path, action, reason)]`.
- It looks up each photo's uploader from its latest `ingest` row and groups by uploader.
- For each uploader, it sends one email (subject "D3 Studio: N ảnh bị trả về") listing the photo paths, the action and the reasons, with a link to `/quan-tri`.
- When there's no SMTP or no uploader, it writes one log line per uploader.
- It never raises, the same rule as the lead notices.

### 5. Frontend
- **`STATUS_VI`** adds `noi_bo: 'Lưu nội bộ'`. `NEXT_STATUS` is unchanged, so `canAdvance` is false there.
- **Card buttons** (approvers only):
  - "Trả về nháp" on cards in in_review, approved or cleared;
  - "Lưu nội bộ" in approved or cleared;
  - "Mở lại" in noi_bo.

  The bulk bar gets "Trả về nháp N mục" next to "Chuyển".
- **The reason dialog** is a native `<dialog>`:
  - a title naming the action and the count;
  - a labelled `<textarea>` with `maxlength=500` and a live counter;
  - a client check (≥ 5 characters) with the error under the field;
  - "Xác nhận" / "Huỷ".

  Esc and Huỷ return focus to the opening button.
- **The card** shows the reason block when `ly_do_duyet` is set ("Bị trả về / Lưu nội bộ / Mở lại · email · time: reason").
- **The Nháp view** has a "Chỉ ảnh bị trả về" checkbox, which reloads with `tra_ve=1`.
- **The page** gets `page-top`.

## Risks / Trade-offs

- **[A reason with personal data]** Reviewers might type client names. → It is staff-only and in the log, the same as captions. The public field list never includes it.
- **[Uploader unknown]** Photos ingested by scripts have no `ingest` row with a user. → The notice goes to the log only.
- **[Old drafts have no reason]** Only drafts returned after this change show the mark. That is expected.

## Migration Plan

- `schema.sql`: `ALTER TABLE space ADD COLUMN IF NOT EXISTS ly_do_duyet jsonb`. Re-apply it, then rebuild backend and web.
- **Rollback:** the column is additive. A `noi_bo` row would show as an unknown status in the old UI. Reopen such photos before rolling back.
