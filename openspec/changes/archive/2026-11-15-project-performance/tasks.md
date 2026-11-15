# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.

Tests use throw-away folders (`test_ps_*`) of published spaces, consented sessions, review_log rows and leads, all removed afterwards. Numbers are checked for those folders only, so real data does not interfere.

## 1. Backend

- [x] 1.1 Create `backend/pipeline/project_stats.py` with `overview(conn, days, user_id=None)`: views and saves of published photos per folder (consented, period), save rate, distinct leads from the three sources, publish date from `review_log`, and the status rule with `WINDOW` / `LOW` / `MIN_COMPARE` and the `D3_PROJECT_REVIEW_DAYS` override.

  Verify with tests on throw-away folders:
  - 12 views and 3 saves give a 25% rate;
  - quiz picks and events older than the period are not counted;
  - a draft photo's views are not counted;
  - a brief with photos of two folders counts once for each;
  - a lead naming `du_an` with dashes counts for the matching folder, and one naming `space_id` counts for its folder;
  - four folders aged over 30 days with 40/30/20/6 views mark only the one with 6 as `can_xem_lai`;
  - a folder 10 days old is `dang_theo_doi` with 20 days left;
  - fewer than 3 eligible folders gives no `can_xem_lai`;
  - `cua_toi` keeps only the caller's folders.
- [x] 1.2 Add `detail(conn, folder, days)`: photos with views and saves, most viewed first, with a no-views mark; and the suggestions `thieu_loai_cong_trinh`, `thieu_muc_dau_tu`, `phong_cach_chua_ro`, `it_anh`, `anh_chua_ai_xem` and `mo_ta_ngan`, each with photo ids and a link.

  Verify with tests:
  - each suggestion fires on a folder built to trigger it, and none fire on a complete folder;
  - photo order and the no-views mark are right;
  - an unknown or unpublished folder gives `None`.
- [x] 1.3 Add `GET /analytics/projects` and `GET /analytics/projects/{folder}`.

  Verify with API tests:
  - architect, lead_architect, admin and sales get 200;
  - visitor and content get 403, and anonymous 401;
  - `days=10` gives 422;
  - an unknown folder gives 404;
  - the JSON holds no `phien_id` and no lead contact;
  - `co_du_lieu_mo_phong` follows the demo sessions.

## 2. Frontend

- [x] 2.1 In `src/api.js`, add `getProjectStats` and `getProjectDetail`. Create `ProjectStatsView.vue`:
  - the period switch;
  - "Chỉ dự án tôi tải lên";
  - the demo banner;
  - a table at 1280px and cards on a phone;
  - status badges;
  - expandable rows with the photo strip and the suggestions, which link to `/quan-tri#p-<folder>`.

  Add the route, "Hiệu quả dự án" in `SiteNav.vue` (`STAFF` and `SALES`), a link from `TrendsView.vue`, and an anchor id on each project heading in `ReviewView.vue`.

  Verify in the browser with demo activity loaded and `D3_PROJECT_REVIEW_DAYS=0`:
  - a sales user sees every published project with numbers that match the API;
  - switching to 90 days changes the numbers but not the status;
  - expanding a project shows its photos and suggestions, and a suggestion link opens `/quan-tri` scrolled to that project;
  - the "Cần xem lại" rows come first;
  - the keyboard expands and collapses a row;
  - 360px has no sideways scroll;
  - a visitor is redirected.

  Remove the demo activity afterwards.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - roadmap 3.5;
  - BFD 5.4 and act-1 status;
  - the API table;
  - the `D3_PROJECT_REVIEW_DAYS` setting;
  - the folder ≠ `/du-an` project note.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
