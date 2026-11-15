# Design

## Context

- **Projects.** A project is the first path segment of `space.relative_path` (the folder), as in the review screen (`projectOf`) and `GET /projects/{folder}/spaces`. Today there are 9 folders with published photos (40 photos).
- **Publish dates.** Each photo's publish time is its `review_log` row with `action='advance' AND detail->>'to'='published'`. A project's publish date is the earliest of these.
- **Behaviour.** `su_kien` holds consented `xem_khong_gian` / `luu_anh` (and `chon_trac_nghiem`, which is not counted, as in the interest score) with `space_id` and `created_at`. Demo sessions are `phien_id LIKE 'demo-%'`. The trend dashboard counts them and shows a banner.
- **Leads.**
  - `lead.ngu_canh` holds `{trang, du_an (site slug), space_id}` for form, chat and brief leads.
  - `lead.bo_suu_tap_id` points to the sent copy, whose photos are in `bo_suu_tap_anh`.
  - A slug becomes a folder by turning `-` into `_` (`folderOf` in `src/lib/projectSpaces.js`).
- **Who uploaded.** `review_log` rows with `action='ingest'` hold `user_id`.
- **Tags.** Manual tags `loai_cong_trinh` and `muc_dau_tu` live in `space_gia_tri` with `nguon_tao='nguoi'`. `space.style_confidence` holds the AI's confidence. Captions are on `space.caption`.
- **Roles:** `STAFF = architect, lead_architect, admin`; `SALES = sales, lead_architect, admin`.

## Goals / Non-Goals

**Goals:**
- per-project numbers that agree with the trend dashboard's way of counting;
- the act-1 30-day check with actionable suggestions;
- no new tables.

**Non-Goals:**
- per-day charts;
- anonymous per-photo counts;
- emailing the list;
- linking folders to the 64 static `/du-an` projects.

## Decisions

### 1. One module, computed on request
`pipeline/project_stats.py`:
- `overview(conn, days, user_id=None)` → `{projects: [...], co_du_lieu_mo_phong, so_sanh: {median_views, du_an_du_tuoi}}`;
- `detail(conn, folder, days)` → `{project, photos: [...], goi_y: [...]}`.

A handful of grouped queries runs per request, the same approach as `trends.overview` (the data is tens of rows).

### 2. Counting
- **Views and saves:** `su_kien` rows of type `xem_khong_gian` / `luu_anh` in the period, joined to published spaces and grouped by folder (and by space, for the detail).
- **Save rate:** saves / views, rounded to a whole percent, or `null` without views.
- **Leads:** the distinct lead ids per folder from the union of three sources:
  1. the folder named by `replace(ngu_canh->>'du_an', '-', '_')`;
  2. the folder of `ngu_canh->>'space_id'`;
  3. the folders of the photos in the brief's copy (`bo_suu_tap_anh` through `lead.bo_suu_tap_id`).

  Each source is restricted to `lead.created_at` in the period.
- **Published date:** `min(review_log.at)` per folder over the publish rows. Photos published before `review_log` existed have no row; for those the project falls back to the folder's earliest `ingest` row, and the page shows "≈".

### 3. Status rule
- **Age** = days since the publish date. The "eligible" projects are those with an age ≥ `WINDOW` (30).
- **Below the line:** views in the last 30 days, always this window whatever period is shown, so the status does not change with the period switch. A project is below the line when its views are < 0.5 × the median views of the eligible projects.
- **Labels:** `can_xem_lai` when eligible and below the line, `dang_theo_doi` when age < 30 (plus `con_ngay`), `on` otherwise.
- **Too few to compare:** with fewer than 3 eligible projects no project is `can_xem_lai`, since there is no fair comparison.
- **Constants** live in the module (`WINDOW = 30`, `LOW = 0.5`, `MIN_COMPARE = 3`). `D3_PROJECT_REVIEW_DAYS` overrides `WINDOW` for a demo, where every project is newer than 30 days. That override is the only way to show a flagged project without waiting 30 days.

### 4. Suggestions
`detail()` returns a list of `{ma, text, so_anh?, link}`. The link is `/quan-tri#<folder>`; the review page scrolls to that project's group, using a hash anchor added to each group heading.

| ma | Fires when |
| :-- | :-- |
| `thieu_loai_cong_trinh` / `thieu_muc_dau_tu` | no photo of the folder has that manual tag |
| `phong_cach_chua_ro` | photos whose `design_style` is `Khac` (any case) or whose `style_confidence < 0.5` |
| `it_anh` | published photos < 0.5 × the median published photos per project |
| `anh_chua_ai_xem` | the photos with 0 views in the period, while the project has > 0 |
| `mo_ta_ngan` | captions shorter than 0.5 × the median caption length of the folder's published photos |

Each suggestion carries the photo ids it is about, so the page can mark those photos.

### 5. API
| Endpoint | Role | Answer |
| :-- | :-- | :-- |
| `GET /analytics/projects?days=30\|90&cua_toi=false` | `architect`, `lead_architect`, `admin`, `sales` | the overview. With `cua_toi=true`, only folders with an `ingest` row by the caller |
| `GET /analytics/projects/{folder}?days=` | same | 404 when the folder has no published photo. The folder is matched exactly; no pattern is needed, because the folder is only a query parameter value |

`days` is a 422 unless it is 30 or 90.

### 6. Frontend
- **`ProjectStatsView.vue`** at `/quan-tri/hieu-qua`, using `page-top` and `meta.roles: ['architect','lead_architect','admin','sales']`.
- **The page:**
  - a period switch (30/90) and "Chỉ dự án tôi tải lên" (for staff who upload);
  - the demo banner;
  - a short line on how the status works ("so với các dự án đã đăng hơn 30 ngày");
  - on wide screens, a table with columns Dự án, Ảnh, Ngày đăng, Lượt xem, Lưu, Tỉ lệ lưu, Khách tiềm năng, Trạng thái;
  - below 760px, stacked cards.
- **The project name** is the matching static project's name when `projectBySlug(slugOf(folder))` exists; otherwise the folder name with spaces.
- **Expanding a row** (a button with `aria-expanded`) loads the detail: a photo strip with views, saves and a "chưa ai xem" mark, then the suggestions with links.
- **Nav:** `SiteNav` adds "Hiệu quả dự án" for `STAFF` and `SALES`. The trend dashboard links to it.
- **`ReviewView`** gets `:id="'p-' + g.project"` on each project heading, so the suggestion links land on the right group.

## Risks / Trade-offs

- **[Consented views only]** The numbers are lower than the real traffic. → This matches the trend dashboard. The page states "lượt xem của khách đã đồng ý", and the status compares projects with each other, so the ratio still works.
- **[Few projects]** A median over 4–9 projects is noisy. → `MIN_COMPARE = 3`, and the rule is only a prompt to look, never an automatic action.
- **[Folder ≠ site project]** A lead from `/du-an/<slug>` counts only when a folder has the same name. → This is stated on the page and in the proposal; it gets fixed by `ingest_projects.py` (roadmap).
- **[Demo data inflates the numbers]** → A banner, the same as the trend dashboard.

## Migration Plan

- No schema change. Rebuild the backend and web. For a demo, run `python -m pipeline.demo_activity` and optionally set `D3_PROJECT_REVIEW_DAYS=0` so the status rule has eligible projects.
- **Rollback:** remove the route and the endpoints. Nothing is stored.
