# Tasks

Backend tests: `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`. Frontend: `docker compose build web`; vitest in a throwaway `node:22-alpine` container on a copy of the sources. Browser checks use the scratchpad Playwright pattern at 1280px and 360px.

## 1. Save events

- [x] 1.1 Widen the `su_kien.loai` CHECK to `('xem_khong_gian', 'luu_anh')` and add indexes on `su_kien(created_at)` and `bo_suu_tap(loai, created_at)` in `backend/schema.sql` (idempotent). Widen the `Event` Literal in `backend/api.py` and reject `phien_id` values starting with `demo-`. Verify with tests in `tests/test_trends.py`: a consented `luu_anh` is stored with the snapshot; a non-consented one bumps `su_kien_an_danh` for `luu_anh`; a `demo-` id gives 422; `tests/test_events.py` still passes.
- [x] 1.2 Add `trackSave` to `src/api.js` and call it from `lib/collection.js::add()` after a successful add (not for staff, not on remove). Verify with a test in `collection.test.js` that add calls `trackSave` once and remove does not; vitest passes.

## 2. Interest score and overview

- [x] 2.1 Create `backend/pipeline/trends.py` with the weights, the per-value score and share, the weekly series, the trend rule and alerts as pure functions, plus `overview(conn, days)`. Verify with unit tests: the spec's weighted score (21), shares (70/30, Khác dropped), the rising example (+140%, "đang tăng"), the too-little case (no label), "mới nổi", and "đang giảm".
- [x] 2.2 Add `GET /analytics/overview?days=` (sales, approvers; days in 7, 30, 90). Verify with tests using inserted events with past timestamps: totals (consented and anonymous views, saves, briefs, leads by source), ranking order and counts, 8 weekly lead buckets, top 5 viewed published spaces; 403 for a visitor, 401 anonymous, 422 for `days=10`; no `phien_id` anywhere in the JSON.

## 3. Demo activity

- [x] 3.1 Create `backend/pipeline/demo_activity.py` (generate, re-run replaces, `--remove`), add `co_du_lieu_mo_phong` to the overview, and exclude `demo-%` sessions in `discovery.py`. Verify with tests: generating creates `demo-` sessions over 8 weeks; re-running doesn't grow the count; the overview flags demo data and shows at least one rising style; `--remove` leaves real sessions untouched and clears the flag; discovery's behaviour count ignores demo events.

## 4. Dashboard page

- [x] 4.1 Add `getOverview` to `src/api.js`, create `TrendsView.vue` at `/quan-tri/xu-huong` (`meta.roles: SALES`), and add the "Xu hướng" role link in `SiteNav.vue`. Include the period switch, total tiles, alerts, dimension cards with bars and trend labels, leads per week with a legend, top spaces and the demo banner. Verify in the browser with demo data loaded: a sales user sees every section; switching to 7 days changes the totals but not the trend labels; the rising style is in the alerts; a top space opens its page; a visitor account sees no link and is redirected; no horizontal scroll at 360px.

## 5. Docs and integration

- [x] 5.1 Update `TONG-QUAN-DU-AN.md`: UC21/UC22 status, roadmap phase 3 items, the API table, and the demo commands (generate and remove) with the warning to remove before real use. Verify that `/openapi.json` lists `/analytics/overview` and that the documented commands run as written.
- [x] 5.2 Run the integration check: full backend suite (only known failures), vitest, the lead-intake, collection and estimate browser scripts, and the dashboard checks. Leave the database without demo data at the end (`--remove`). Verify and record the results here. Result: backend 152 passed and 8 failed, the same known 8; vitest 35/35; browser scripts dashboard 11/11 (with demo data), lead-intake 30/30, collection 31/31, estimate 19/19. Demo data removed at the end (0 `demo-` sessions) and the price table back to 60 sample rows. Fixed along the way: `days` as a Literal of ints refused the query string "7"; the demo rise was unreliable with uniformly random session dates (now an equal number of sessions per week, rising in 5/5 seeds). Not fixed, outside this change: the header for staff with every role link overflows at 1280px.
