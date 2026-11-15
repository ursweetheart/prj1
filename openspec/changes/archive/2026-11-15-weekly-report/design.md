# Design

## Context

- **Email.** `pipeline/notify.py` has `_smtp_ready()` and `_send(to, subject, body)`: plain-text email over SMTP with STARTTLS, set up by the `D3_SMTP_*` settings. Without `D3_SMTP_HOST`, notices are logged instead. Every notice function catches its own errors.
- **Counts.**
  - `trends.overview(conn, days)` returns `tong` (views, saves, briefs, leads by source), `chieu` (scored values per dimension, highest first), `canh_bao` (trend alerts for the last 7 days against the 4 weeks before) and `co_du_lieu_mo_phong`.
  - `project_stats.overview(conn, 30)` returns each project's `trang_thai` and `luot_xem_cua_so`.
- **Accounts.** `app_user` has `role`, `bi_khoa` (locked) and `email`. Facebook-only accounts use `facebook-<id>@facebook.invalid`. The roles live in `auth.py`: `APPROVERS = lead_architect, admin`; `SALES = sales, lead_architect, admin`.
- **Runtime.** The backend runs a single uvicorn process (`Dockerfile` CMD) with no scheduler or task queue. The container clock is UTC. Vietnam has no daylight saving, so UTC+7 is a fixed offset.
- **Seq-18:**
  1. the scheduler triggers on Monday at 8:00;
  2. the analytics store is queried for rankings, trends and leads by source;
  4. the report is built and compared with the week before;
  5. a trend-alert section is added;
  6–7. the email is sent to the sales manager.

## Goals / Non-Goals

**Goals:**
- One report per week, sent automatically, never twice.
- The same counts as the dashboards.
- Recipients that follow the accounts.
- An admin can see what was sent and try it safely.

**Non-Goals:**
- HTML email.
- Choosing the day or time in the UI.
- Monthly or custom reports.
- Per-recipient content.
- An unsubscribe link that works without signing in.
- Retrying failed recipients.

## Decisions

### 1. One module, `pipeline/weekly_report.py`
- `week_bounds(now)` returns `(start, end)` of the last full week: Monday 00:00 to the next Monday 00:00 in UTC+7, as aware datetimes.
- `build(conn, now)` returns `{tuan_bat_dau, subject, body, so_lieu}`. It is pure apart from its queries, so tests can pass a fixed `now`.
- `recipients(conn)` returns a list of emails.
- `send_week(conn, now, force_to=None)` records and sends. It returns the log row, or `None` when this week is already done.
- `due(now)` is true when `now` (UTC+7) is Monday 08:00 or later in the current week. Since the week starts on Monday, that means any time from Monday 08:00 to Sunday 24:00.

### 2. Content and counts
- **Totals use exact week bounds**, from their own small queries:
  - views and saves: consented `su_kien` plus anonymous `su_kien_an_danh` by day, as the dashboard's `tong` does;
  - briefs: `bo_suu_tap` with `loai='da_gui'`;
  - leads: `lead` grouped by `nguon`.
  
  Each query runs for `[start, end)` and for the week before.
- **Change** = `round(100 × (this − before) / before)`. When `before = 0` and `this > 0`, it reads "mới", and when both are 0, "–".
- **Alerts and the top 3 values** reuse `trends.overview(conn, 7)`: `canh_bao`, and the first 3 `gia_tri` of the dimensions `phong_cach` and `khong_gian` (by `ma`). They are computed at send time, so their 7-day window ends Monday at about 08:00. That is 8 hours off the calendar week, which is accepted so the report matches what the dashboard shows that morning.
- **"Cần xem lại" projects** come from `project_stats.overview(conn, 30)`, as names and 30-day views.
- **Text:** the subject is `[D3] Báo cáo tuần dd/mm – dd/mm`. The body is in Vietnamese, with:
  - sections in seq-18 order: tổng quan → cảnh báo xu hướng → được quan tâm nhất → dự án cần xem lại → links;
  - an empty section saying "Không có …";
  - a footer: "Tắt báo cáo này: mở /quan-tri/xu-huong, bỏ chọn «Nhận báo cáo tuần qua email»".

  The demo note goes first when `co_du_lieu_mo_phong` is set.

### 3. Once per week: claim a row first
Table `bao_cao_tuan`:
- `tuan_bat_dau date PRIMARY KEY` (the Monday);
- `gui_luc timestamptz`;
- `so_nguoi_nhan int`;
- `so_loi int`;
- `ket_qua text CHECK IN ('dang_gui','da_gui','loi_mot_phan','loi','chi_ghi_log')`;
- `tieu_de text`;
- `noi_dung text`.

`send_week` first runs `INSERT … ON CONFLICT DO NOTHING RETURNING` with `ket_qua='dang_gui'` and commits. If no row comes back, the week is already taken and it returns `None`. It then sends to each recipient, catching errors per recipient, and updates the row with the result:
- `chi_ghi_log` when SMTP is not configured;
- `da_gui` when every send succeeded;
- `loi_mot_phan` when some failed;
- `loi` when all failed, or when there were no recipients.

A crash between the claim and the update leaves `dang_gui`, which is shown as is. The week is not retried, so nobody gets a second copy; it is a visible failure, not a silent one.

The test send (`force_to`) does not touch the table.

### 4. Scheduler: an asyncio loop in the app lifespan
`api.py` gets a FastAPI `lifespan` that starts `asyncio.create_task(_weekly_loop())`, unless `D3_WEEKLY_REPORT=off` or the app runs under pytest (tests call the module directly). The loop:
- every 10 minutes, if `due(now)`, runs `send_week` in a thread (`asyncio.to_thread`, since the work is blocking psycopg and SMTP);
- also runs once 30 seconds after startup, which covers "the server was down on Monday";
- catches and logs every exception, so the loop never dies.

**Alternatives:**
- cron in another container: more moving parts for a student project;
- APScheduler: a new dependency for a single job.

The database claim also makes two processes safe, should someone run more workers.

### 5. Recipients and opt-out
- **Column:** `app_user.nhan_bao_cao_tuan boolean NOT NULL DEFAULT true`.
- **Recipients:** `role IN ('sales','lead_architect','admin') AND NOT bi_khoa AND nhan_bao_cao_tuan AND email NOT LIKE '%.invalid'`, ordered by id.
- **Opt-out:**
  - `GET /me/weekly-report` → `{nhan: bool}`;
  - `PUT /me/weekly-report {nhan: bool}`;
  - both for `SALES` only (403 for others, 401 anonymous).
- **The log line** for each send names the recipient count, never the addresses.

### 6. Admin endpoints (`APPROVERS`)
| Endpoint | Answer |
| :-- | :-- |
| `GET /reports/weekly` | the last 8 rows: week, `gui_luc`, `so_nguoi_nhan`, `so_loi`, `ket_qua`, `tieu_de`. Not the body, which the preview shows |
| `GET /reports/weekly/preview` | `{tieu_de, noi_dung, nguoi_nhan: count}` for the last full week, built now |
| `POST /reports/weekly/test` | sends the preview to the caller's own email only. 409 when SMTP is not configured; otherwise `{gui_toi: email}` |

### 7. Frontend
`TrendsView.vue`:
- **For every SALES user**, a box "Nhận báo cáo tuần qua email (thứ Hai, 8:00)", loaded from and saved to `/me/weekly-report`.
- **For APPROVERS, a "Báo cáo tuần" card** (`WeeklyReportPanel.vue`) with:
  - a table of the last 8 sends (it becomes stacked lines on a phone);
  - "Xem trước", which opens the text in a `<pre>` with wrapping;
  - "Gửi thử cho tôi", which shows the result, or "Chưa cấu hình email" on 409.

The page also gets `.page-top` (as the newer admin pages have), if a browser check shows the title under the fixed header.

## Risks / Trade-offs

- **[A crash mid-send leaves `dang_gui`]** → It is shown in the log card. There is no automatic retry, by choice, so nobody gets a duplicate.
- **[Alerts window ≠ calendar week]** → The difference is a few hours. It is stated in the design, and the totals use exact bounds.
- **[The test send reveals the report to whoever presses it]** → Only APPROVERS can, and it goes only to their own account email.
- **[An in-process scheduler stops when the backend is down]** → Covered by the startup check for the current week. Earlier weeks are not backfilled (spec).
- **[Tests must not send real mail]** → The loop is off under pytest. Module tests monkeypatch `notify._send` and the SMTP settings.

## Migration Plan

- Apply `schema.sql`, which adds the column and the table; both can be re-run.
- Rebuild the backend.
- With SMTP set, the first report goes out the next Monday from 08:00. A report for the current week is sent at the first check after the deploy, if the deploy is on Monday 08:00 or later.
- **Rollback:** set `D3_WEEKLY_REPORT=off`. The column and table are harmless.
