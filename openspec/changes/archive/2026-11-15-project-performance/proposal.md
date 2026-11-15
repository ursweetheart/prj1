# Proposal

## Why

QT-01 does not end at publishing. act-1's last steps are "Theo dõi hiệu quả sau 30 ngày → Lượt xem dưới ngưỡng? → Đề xuất chỉnh tiêu đề, ảnh đại diện hoặc nhãn", and BFD 5.4 asks for the results of each project after it is published. The trend dashboard (`/quan-tri/xu-huong`) answers "which styles and materials do visitors like". Nothing answers "how is *this* project doing, and what should we change about it". So an architect cannot tell whether the project they published last month is being seen, saved or asked about. This is roadmap item 3.5.

## What Changes

- **A page `/quan-tri/hieu-qua`** for architects, the lead architect, admin and sales. For a period of 30 or 90 days it shows one row per project (photo folder) with published photos:
  - the number of published photos and when the project was published;
  - consented views, saves and the save rate;
  - the leads it brought;
  - a status.
- **Leads per project** count distinct leads that came from that project's page, named one of its photos, or sent one of its photos in a brief.
- **A project's detail** (expand the row):
  - each published photo with its views and saves in the period, most-looked-at first;
  - the photos nobody looked at;
  - suggestions.
- **The 30-day check (act-1)**:
  - A project published at least 30 days ago whose views in the last 30 days are under half the median of such projects is "Cần xem lại" (needs attention).
  - A project published less than 30 days ago is "Đang theo dõi" (watching), with the days left.
  - Otherwise it is "Ổn".
- **Suggestions:** concrete, from the project's own data, and each one links to where it is fixed in `/quan-tri`:
  - the project has no "Loại công trình" or "Mức đầu tư" tag, so filters on those miss it;
  - photos tagged with the style "Khác" or with a low style confidence;
  - fewer published photos than most projects;
  - photos with no views in the period;
  - a caption much shorter than the others.
- **"Chỉ dự án tôi tải lên"** (only projects I uploaded): architects can narrow the list to projects with photos they uploaded.
- **Demo data:** while demo activity exists, the page shows the same "Đang hiển thị cả dữ liệu mô phỏng" banner as the trend dashboard.

## Capabilities

### New Capabilities
- `analytics/project-performance`: per-project results, the per-photo detail, the 30-day attention check and its suggestions, and who can see them.

### Modified Capabilities
None. `analytics/trend-dashboard` and `analytics/interest-score` keep their rules. This page reads the same consented events and counts views and saves the same way.

## Impact

- **Backend:**
  - new `backend/pipeline/project_stats.py`;
  - `backend/api.py`: `GET /analytics/projects?days=30|90&cua_toi=`, `GET /analytics/projects/{folder}?days=`;
  - new `backend/tests/test_project_stats.py`.
- **Frontend:**
  - `src/api.js`;
  - new `src/views/ProjectStatsView.vue`;
  - `src/router/index.js`;
  - `src/components/SiteNav.vue` ("Hiệu quả dự án");
  - a link from `/quan-tri/xu-huong`.
- **No schema change.** The publish date comes from `review_log` (`action='advance'`, to `published`), views and saves from `su_kien`, and leads from `lead.ngu_canh` and `lead.bo_suu_tap_id`.
- **Known limit:** "project" means the photo folder in the database, as on the review screen. Those folders are not linked to the 64 static projects on `/du-an` until `ingest_projects.py` is run over the site photos. A lead from a `/du-an/<slug>` page counts for the folder whose name equals the slug with `-` turned into `_`.
- **Out of scope:**
  - anonymous views per project (only daily totals are kept without consent);
  - time spent on a page;
  - choosing a cover photo (there is no cover in the data yet);
  - emailing the "Cần xem lại" list (that belongs with the weekly report, roadmap 3.4).
