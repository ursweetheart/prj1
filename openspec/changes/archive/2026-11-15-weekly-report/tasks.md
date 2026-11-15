# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Schema:** re-apply it with `docker compose exec -T db psql -U d3 -d d3 -q -v ON_ERROR_STOP=1 < backend/schema.sql`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.
- **Tests never send real mail:** `notify._send` is monkeypatched to collect messages, and the SMTP settings are set or cleared per test.
- **Throw-away data:** test accounts use `@example.com`; test rows in `bao_cao_tuan` use weeks far in the past (e.g. 2001) and are deleted afterwards.

## 1. Backend

- [x] 1.1 Schema: add `app_user.nhan_bao_cao_tuan boolean NOT NULL DEFAULT true`, and table `bao_cao_tuan` (`tuan_bat_dau date PK`, `gui_luc`, `so_nguoi_nhan`, `so_loi`, `ket_qua` CHECK `dang_gui|da_gui|loi_mot_phan|loi|chi_ghi_log`, `tieu_de`, `noi_dung`).

  Verify that `schema.sql` applies twice without errors.
- [x] 1.2 Create `backend/pipeline/weekly_report.py` with `week_bounds(now)`, `due(now)`, `build(conn, now)` and `recipients(conn)`.
  - `build` gives the exact-week totals with the change from the week before ("mới" / "–"), the alerts and top 3 of `phong_cach` / `khong_gian` from `trends.overview(conn, 7)`, the "Cần xem lại" projects from `project_stats.overview(conn, 30)`, the demo note, the links and the opt-out footer.

  Verify with tests:
  - `week_bounds` for a Wednesday in UTC+7 gives the Monday 00:00–Monday 00:00 before it, and Sunday 23:30 UTC+7 still belongs to the current week;
  - `due` is false at Monday 07:30 and true at Monday 08:00 and on Tuesday;
  - with throw-away events dated last week (120 views) and the week before (100), the change is +20% *relative to the counts the test adds* (check the difference over real data, as `test_trends` does);
  - saves only in the last week show "mới";
  - with no alerts, the sections say "Không có";
  - the body never contains a test lead's email, name or a session id;
  - the demo note shows exactly when demo sessions exist.
- [x] 1.3 Add `send_week(conn, now, force_to=None)`: claim the week's row, send to each recipient separately, catch errors per recipient, and record the result (`chi_ghi_log` / `da_gui` / `loi_mot_phan` / `loi`). `force_to` sends only to that address and writes no row.

  Verify with tests:
  - recipients include only active sales / lead_architect / admin accounts with the box on, and not `.invalid` addresses;
  - each gets their own message;
  - a second `send_week` for the same week sends nothing and returns `None`;
  - without SMTP, the row is `chi_ghi_log` and the text is in the `d3.report` log;
  - one failing recipient gives `loi_mot_phan` with `so_loi=1`, and the others still get it;
  - a test send writes no row, and the week can still be sent afterwards.
- [x] 1.4 Scheduler in `api.py`: a `lifespan` that starts the loop (a check 30 s after startup, then every 10 minutes; `asyncio.to_thread(send_week)` when `due`; every exception logged), skipped when `D3_WEEKLY_REPORT=off` or under pytest.

  Verify:
  - the backend starts and logs that the scheduler is on;
  - with `D3_WEEKLY_REPORT=off`, it logs that it is off;
  - after a restart in a due week, the log shows one report, `bao_cao_tuan` has one row for the week, and a second restart adds none. Use a compose override in the scratchpad; SMTP is not configured, so nothing is mailed.
- [x] 1.5 Endpoints:
  - `GET/PUT /me/weekly-report` (SALES);
  - `GET /reports/weekly`, `GET /reports/weekly/preview`, `POST /reports/weekly/test` (APPROVERS; 409 without SMTP).

  Verify with API tests:
  - roles: 403 for visitor, architect and content on all of them, and for sales on the `/reports` ones; 401 when anonymous;
  - turning the report off removes the user from `recipients`, and turning it on adds them back;
  - the preview has a subject, a body and a recipient count;
  - the log lists at most 8 rows, newest first, without the body;
  - the test send goes only to the caller.

## 2. Frontend

- [x] 2.1 In `src/api.js`, add `getWeeklyOptIn`, `setWeeklyOptIn`, `listWeeklyReports`, `previewWeeklyReport` and `testWeeklyReport`.
  - **Box for every SALES user:** in `TrendsView.vue`, the box "Nhận báo cáo tuần qua email (thứ Hai, 8:00)".
  - **New `WeeklyReportPanel.vue` for APPROVERS:** the log table (stacked lines on a phone), "Xem trước" (`<pre>`, wrapped) and "Gửi thử cho tôi" ("Chưa cấu hình email" on 409).
  - Use `.page-top` on the trend dashboard if the title sits under the fixed header.

  Verify in the browser:
  - a sales user sees the box but not the panel; unticking it survives a reload;
  - the lead architect sees the panel, the preview shows the report text, and the test send without SMTP shows "Chưa cấu hình email";
  - the log shows the week sent in 1.4;
  - at 360px there is no sideways scroll, including the preview;
  - the title is below the header at 360px and 1280px.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - UC23;
  - seq-18;
  - roadmap 3.4;
  - the API table;
  - the `D3_WEEKLY_REPORT` setting and how to see a report without SMTP (the log);
  - the note that the first report goes out at the first check after deploy in a due week.

  Also add `D3_WEEKLY_REPORT` to `backend/.env.example`.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
