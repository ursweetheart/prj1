# Proposal

## Why

The site has two kinds of "project" that never meet (roadmap 0.1, technical debt 9.1):
- **`/du-an`** shows 64 projects from `src/data/projects.js`, with 626 photos in `src/assets/projects/<slug>/`.
- **The backend** treats a photo folder in `image_d3/` as a project: 10 folders and 154 photos (`hanjadin`, `Indochine`, `luxury`, …).

`project-space-sync` set the rule that a site photo `<slug>/<file>` is the space `<slug with _>/<file>`, but `ingest_projects.py` was never run. The existing folders are named differently, so none of them matches a site project. As a result:
- **No Lightbox link:** no published photo has a "Chi tiết không gian" link on `/du-an`.
- **Project performance:** `/quan-tri/hieu-qua` lists folders such as `hanjadin`, not projects, and leads sent from `/du-an/<slug>` are never counted.
- **Assistant cards:** they can never open a project page.
- **Quiz:** it can't suggest projects (seq-12 step 12).
- **UC02 project details:** area, rooms, build time and investment level have nowhere to live.

Running the ingest as it stands would make it worse. At least 6 of the existing folders hold Behance photos of the same projects (`hanjadin` ↔ `hanjadin-apartment`, `wallnut` ↔ `wallnut-villa`, …). They would be analysed a second time as new spaces, which costs one Gemini call each and duplicates them in search, chat and the quiz.

## What Changes

- **A project table `du_an`.** Each row has:
  - slug, name, type (`loai`), year and short description, as on the site, plus display order and whether it has a page on the site;
  - project details staff fill in: area in m², bedrooms, build time, investment level (a `muc_dau_tu` taxonomy value) and the design concept text (`thuyet_minh`).
  - **Folder-only projects:** a photo folder with no site project, for example one created by an upload at `/quan-tri`, gets a row of its own with no page.
- **A sync command `sync_projects.py`.**
  - It reads `src/data/projects.js` (read only) and adds or updates the site fields, keeping the site's order. It never overwrites what staff entered.
  - **Photo matching:** it links each site photo to the stored space that shows the same picture, by visual similarity on the existing SigLIP2 embeddings. A matched space records its project and site file name.
  - **New photos:** only site photos that match nothing become new draft spaces. That needs `--ingest` and costs one Gemini call per photo.
  - It has `--dry-run`, logs every link it makes and is safe to run again.
- **Project APIs.**
  - `GET /projects` returns the projects with at least one published photo (visitors) or all projects (staff).
  - `GET /projects/{slug}` returns the project's fields and its published spaces in the site's photo order.
  - `PUT /projects/{slug}` lets the lead architect and admin edit the project details. Every change is logged.
  - **Kept:** `GET /projects/{folder}/spaces` keeps working.
- **Consumers read the catalog instead of the folder name.**
  - **Project performance:** one row per project with its name and slug. A lead that names `/du-an/<slug>` counts for that project.
  - **Assistant cards:** cards carry the project's slug and name.
  - **Quiz:** the result suggests up to 3 projects.
- **Not in this change:** switching `/du-an` and the project page to the API, and showing the project details to visitors. Those are frontend pages owned by Tùng. The API is ready for them; the static build keeps reading `projects.js`.

## Capabilities

### New Capabilities
- `project-catalog`: the project table, the sync from the site's project list with photo matching, the project read and edit APIs, and how a photo belongs to a project.

### Modified Capabilities
- `analytics/project-performance`: a project is a catalog project, not a photo folder. Rows show its name, and leads from its page count.
- `style-quiz`: the result also suggests projects.

## Impact

- **Database:** a new `du_an` table, two new columns on `space` (`du_an_slug`, `anh_trang`) and a log table `nhat_ky_du_an`. All are additive, using `CREATE … IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` in `backend/schema.sql`.
- **Backend:**
  - new `backend/pipeline/projects.py` and `backend/sync_projects.py`;
  - `ingest_projects.py` is folded into the sync (`--ingest`);
  - routes are added in `backend/api.py`;
  - `pipeline/project_stats.py`, `pipeline/project_results.py`, `pipeline/quiz.py` and `pipeline/weekly_report.py` group by project instead of folder.
- **Cost:**
  - **Matching** runs SigLIP2 on CPU over 626 site photos, a few minutes and no API calls.
  - **`--ingest`** costs one Gemini call per unmatched photo, so it is opt-in and takes `--limit`.
- **Frontend:** none required. `src/data/projects.js` is read, never written. The pending `assistant-project-results` card code can use the slug the API now returns.
- **Docs:** update UC02, UC06, BFD 5.4, roadmap 0.1, item 9.1 and the script table in `TONG-QUAN-DU-AN.md`.
