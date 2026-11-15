# Proposal

## Why

UC23 ("Gửi báo cáo định kỳ") is the last use case in section 5.4 still marked "Chưa". Seq-18 starts with a scheduler that, every Monday at 8:00:
- builds a weekly report from the rankings, trends and leads by source;
- compares it with the week before;
- adds a trend-alert section;
- emails it to the sales manager, who opens the dashboard for detail.

Today the trend dashboard (`/quan-tri/xu-huong`) and the project results (`/quan-tri/hieu-qua`) only help someone who remembers to open them. The "Cần xem lại" list from the last change was left out of scope for this report. This is roadmap item 3.4.

## What Changes

- **A weekly report**, built from the same counts as the two dashboards:
  - **Last week's totals** (Monday to Sunday) and the change from the week before: views, saves, briefs sent, and leads by source.
  - **Trend alerts:** rising, new and falling values, as on the trend dashboard.
  - **The top 3 values** of the style and space-type dimensions.
  - **The projects marked "Cần xem lại"**, each with its views.
  - **Links** to `/quan-tri/xu-huong` and `/quan-tri/hieu-qua`.
  - **A note when demo activity is loaded.**
- **Schedule:** built and sent automatically every Monday from 8:00 Vietnam time (UTC+7).
  - It goes out once per week, even after a restart.
  - If the server was down on Monday, it goes out at the next check that same week.
  - Missed earlier weeks are not sent.
  - The setting `D3_WEEKLY_REPORT=off` turns the schedule off.
- **Recipients:** every active (not locked) account with the role sales, lead_architect or admin, unless they turned it off.
  - Each recipient gets their own email, so addresses are not shared.
  - Facebook placeholder addresses (`@facebook.invalid`) are skipped.
- **Opt-out:** on the trend dashboard, the box "Nhận báo cáo tuần qua email" turns it off or on for yourself. The email says where to find it.
- **Without SMTP:** the report is written to the backend log and marked "chỉ ghi log", the same as lead notices today.
- **For admin and the lead architect, a "Báo cáo tuần" section on the trend dashboard:**
  - the last 8 reports, with week, send time, recipient count and result;
  - "Xem trước", which shows this week's report text without sending it;
  - "Gửi thử cho tôi", which sends it only to the caller and does not count as the week's report.
- **The report holds counts only**, never a visitor's name, contact or session.

**Assumption:** recipients are taken from the accounts, not from a fixed list in `.env`. Nobody has to edit `.env`, and locked or demoted accounts stop receiving it on their own. The existing `D3_SALES_EMAIL` stays only for new-lead notices.

## Capabilities

### New Capabilities
- `analytics/weekly-report`: building the weekly report, its schedule and once-per-week guarantee, recipients and opt-out, the send log, preview and test send.

### Modified Capabilities
None. The trend dashboard and project results keep their rules. The report reuses `trends.overview` and `project_stats.overview` without changing what they count.

## Impact

- **Backend:**
  - new `backend/pipeline/weekly_report.py`, which builds the text, picks recipients, sends and logs;
  - `backend/api.py`:
    - a lifespan background task that checks the time;
    - `GET /reports/weekly` (the log), `GET /reports/weekly/preview`, `POST /reports/weekly/test`;
    - `GET/PUT /me/weekly-report` (opt-out).
  - `backend/pipeline/notify.py`: reuses `_send` and `_smtp_ready`.
  - new `backend/tests/test_weekly_report.py`.
- **Schema:**
  - column `app_user.nhan_bao_cao_tuan boolean NOT NULL DEFAULT true`;
  - table `bao_cao_tuan`, one row per week, unique on `tuan_bat_dau`: send time, recipient count, failure count, result, and the text sent.
- **Frontend:**
  - `src/api.js`;
  - `src/views/TrendsView.vue`: the opt-out box, plus the report section for approvers;
  - possibly a small `WeeklyReportPanel.vue` component.
- **No new dependency.** The scheduler is a plain asyncio loop inside the backend process. The backend runs one uvicorn worker, and the database row is what makes each week go out once.
- **Out of scope:**
  - HTML email (the report is plain text, like the other notices);
  - choosing a different day or time in the UI;
  - monthly reports;
  - per-recipient content;
  - an unsubscribe link that works without signing in.
