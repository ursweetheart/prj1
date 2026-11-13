# Design

## Context

- **Events:** `POST /events` takes `{loai: 'xem_khong_gian', dong_y, phien_id, space_id}`. A consented call upserts `phien_truy_cap` and inserts `su_kien` with `gia_tri text[]` (`dimension:value` snapshot of the published space). A non-consented call increments `su_kien_an_danh(ngay, loai)`. `su_kien.loai` has a CHECK allowing only `xem_khong_gian`. `trackView()` in `api.js` is fire-and-forget.
- **Other signals already stored:** sent briefs (`bo_suu_tap` `loai='da_gui'` with `bo_suu_tap_anh` rows and `created_at`), and leads (`lead.nguon`, `created_at`). Saves of signed-in users sit in `bo_suu_tap_anh` (`dang_luu`); anonymous saves are browser-only, so the server never sees them today.
- **Discovery** (`pipeline/discovery.py` ~line 144) counts `su_kien` rows to score candidate dimensions.
- **Roles:** `SALES = sales + approvers` in the frontend, `require("sales", *APPROVERS)` on the backend (as for `/leads`).
- **Volume:** tens of events today. Even years of a studio site are thousands to low millions of rows, and the queries group by date and by taxonomy value.

## Goals / Non-Goals

**Goals:**
- Numbers a reviewer can recompute by hand: plain weighted counts, no model.
- One endpoint feeding the whole page.
- Demo data that can never be mistaken for real and can be removed in one command.

**Non-Goals:**
- Nightly roll-ups and an analytics store (act-3's "kho phân tích"), the weekly email, and clustering.

## Decisions

### 1. Saves as `luu_anh` events, sent from the collection store
`lib/collection.js::add()` calls `trackSave(spaceId)` after a successful add, the same fire-and-forget call as `trackView` with `loai: 'luu_anh'`. The CHECK on `su_kien.loai` becomes `IN ('xem_khong_gian', 'luu_anh')`, and the `Event` model's Literal is widened.
- Account saves in `bo_suu_tap_anh` are *not* read for the score: they would double count consented saves and would count non-consented ones. Saves count only through consented events, matching the consent promise.
- Staff are excluded as for views (`!hasRole(STAFF)`).

### 2. Compute on request, in SQL, in `pipeline/trends.py`
`overview(conn, days)` runs a few grouped queries:
- **signals per value:** `unnest(gia_tri)` over `su_kien` in the period, grouped by `loai` and value, plus sent-brief photos joined to current `space_gia_tri` (briefs store no snapshot; current tags are close enough for v1);
- **weekly signals per value** for the last 5 weeks (week 0 = last 7 days, weeks 1–4 before);
- **totals:** consented views and saves, anonymous views (`su_kien_an_danh`), briefs (`da_gui` rows), leads by `nguon`;
- **leads per source per week** for 8 weeks;
- **top 5 viewed published spaces.**

Python then applies the weights (`W = {xem: 1, luu: 3, brief: 5}`), shares, the trend rule and the alert list. Taxonomy names come from `gia_tri_phan_loai` / `chieu_phan_loai` (`hien_thi_cho_khach` dimensions only, in `thu_tu` order), and `*:khac` / `*:Khac` are dropped case-insensitively.
- *Alternative:* a nightly roll-up table. Rejected for v1: no scheduler exists, the volume is tiny, and it can be added behind the same function later.
- **Trend rule** (spec): `avg = mean(weeks 1..4)`; `rising` if `w0 ≥ 1.5·avg and signals0 ≥ 5`; `new` if `avg == 0 and signals0 ≥ 5`; `falling` if `avg ≥ 5 and w0 ≤ 0.5·avg`; `change = (w0 − avg)/avg` when `avg > 0`. Thresholds are module constants.

### 3. One endpoint
`GET /analytics/overview?days=7|30|90` (`require("sales", *APPROVERS)`) returns
`{days, tong: {...}, chieu: [{ma, ten, gia_tri: [{ma, ten, diem, ti_le, xem, luu, brief, thay_doi, xu_huong}]}], canh_bao: [...], lead_theo_tuan: [{tuan_bat_dau, form, chat, brief, estimate}], khong_gian_xem_nhieu: [{id, relative_path, space_type, design_style, luot_xem}], co_du_lieu_mo_phong: bool}`.
There is no session id anywhere (spec "Aggregates only").

### 4. Dashboard page
`TrendsView.vue` at `/quan-tri/xu-huong` (`meta.roles: SALES`) contains:
- a period switch (chips);
- a row of total tiles;
- an alerts list;
- one card per dimension with up to 8 rows: name | CSS bar (`width: share%`) | share | small counts | trend arrow (↑ ↓ ✦ with text for screen readers);
- leads per week as a stacked bar per week (CSS flex, colour per source plus a legend);
- top spaces as thumbnails.

The cards sit in a responsive grid, and everything uses existing tokens. Colours for the four lead sources come from existing tokens (`--accent`, `--ink-2`, `--dim`, `--success`), always with a text legend, so colour is never the only cue.

### 5. Demo activity
`pipeline/demo_activity.py`:
- first deletes all `demo-%` sessions (`ON DELETE CASCADE` removes their events);
- creates N sessions (default 240) over 56 days with ids `demo-<hex>`; each picks a "taste", a weighted style choice that shifts towards one rising style (the style with most published spaces that isn't the current leader) in the last 14 days;
- each session views 3–10 published spaces of matching tags and saves about 20% of them;
- writes `gia_tri` snapshots exactly as `/events` does, using the same SQL subquery, and sets `created_at` in the past.

`--remove` only deletes. The overview's `co_du_lieu_mo_phong` is `EXISTS (SELECT 1 FROM phien_truy_cap WHERE id LIKE 'demo-%')`. Discovery's `su_kien` count adds `AND phien_id NOT LIKE 'demo-%'`.
- *Alternative:* a separate demo database. Rejected: the point is showing the real dashboard on the real stack. The prefix plus the banner keep it honest.
- A `demo-` id passes the existing `phien_id` pattern `[A-Za-z0-9_-]{16,64}`, so a browser could in theory send one. The generator's ids are 37 characters of hex after the prefix. The `/events` endpoint rejects ids starting with `demo-`, so real traffic can never be mistaken for demo data or vice versa.

## Risks / Trade-offs

- [Brief photos use current tags, not a snapshot] → Accepted for v1; recorded in the code. Briefs are rare, so the drift is small.
- [Demo data left in the database by mistake] → The banner is shown on every dashboard visit, and the remove command is documented in `TONG-QUAN-DU-AN.md`.
- [Small numbers make percentages jumpy] → The minimum of 5 signals before any trend label.
- [On-request queries grow with traffic] → Indexes on `su_kien(created_at)` and `bo_suu_tap(loai, created_at)`. A nightly roll-up can replace the internals later without changing the endpoint.

## Migration Plan

Re-apply `schema.sql` (the event CHECK and the new indexes), rebuild backend and web, and optionally run `docker compose exec backend python -m pipeline.demo_activity` for a demo. Rollback is to redeploy the previous code; the wider CHECK is harmless to it.
