# Tasks

## 1. Data model

- [x] 1.1 In `backend/schema.sql`, add the following, all additive (`IF NOT EXISTS`):
  - table `du_an`: `slug` PK with a pattern check; `ten`, `loai`, `nam`, `mo_ta_ngan`, `thu_tu`, `co_trang`; `dien_tich_m2 numeric CHECK > 0`, `so_phong_ngu int CHECK > 0`, `thoi_gian_thi_cong text`, `muc_dau_tu text`, `thuyet_minh text CHECK length ≤ 4000`; `cap_nhat_luc`;
  - table `nhat_ky_du_an`: `du_an_slug`, `user_id`, `hanh_dong`, `chi_tiet jsonb`, `luc`;
  - `space.du_an_slug` (FK `ON UPDATE CASCADE`) and `space.anh_trang`, plus an index on `space(du_an_slug)`.

  Verify: run the schema twice on the Docker DB with no error, and the existing `pytest` suite passes unchanged.

## 2. Catalog and sync

- [x] 2.1 Create `backend/pipeline/projects.py` with:
  - `parse_site_projects(text)`, the regex reader of the `PROJECTS = [ … ]` block (design decision 4, with the `shortcut:` comment). It raises on an empty list or an unreadable entry line.
  - `match(site_vecs, space_vecs, threshold=0.95)`, returning the mutual-best pairs with their scores.
  - `folder_project_slug(folder, taken)`.

  Verify with no-network tests in `backend/tests/test_projects_catalog.py`:
  - `parse_site_projects` reads the real `src/data/projects.js` into 64 entries, and rejects a malformed line;
  - `match` keeps a mutual pair at 0.97 and drops a one-way best and a pair at 0.93;
  - `folder_project_slug('Indochine', {'indochine'})` gives `indochine-thu-muc`.
- [x] 2.2 Add read-only mounts of `./src/data` and `./src/assets/projects` to the backend service in `docker-compose.yml` (design decision 4). Verify: `docker compose exec backend ls /src/assets/projects | wc -l` prints 64.
- [x] 2.3 Create `backend/sync_projects.py [--dry-run] [--ingest --limit N]`. It does the following, in order:
  1. Upsert the site fields only (design decision 6).
  2. Mark projects that left the list as `co_trang = false`.
  3. Embed the site photos with `VisionEmbedder`, skipping files whose path and modification time are already in the log.
  4. Link mutual-best matches without overwriting an existing `du_an_slug`, and log each link with its score.
  5. Place the leftovers of a folder by majority (design decision 3), and create folder-only projects for the rest.
  6. With `--ingest`, process up to N unmatched site photos into draft spaces of their project.

  The dry run prints, per project, matched / unmatched counts, the per-folder destinations and the 10 closest non-matches above 0.85, and writes nothing.

  Verify with DB tests that use small fake embeddings, touch only rows the test made, and clean up:
  - a re-run changes nothing;
  - a staff-entered area survives a rename;
  - an existing link isn't overwritten;
  - the majority rule places a leftover;
  - a folder with no match gets a project with no page.
- [x] 2.4 Turn `backend/ingest_projects.py` into a thin wrapper around `sync_projects.py --ingest`, which keeps the `project-space-sync` folder naming for new spaces. In the upload path (`pipeline/store.py` `save_records`), assign a new space to its folder's project, creating a project with no page when none exists. Verify: a test upload into a new folder creates the project and links the space; the existing upload tests pass.

## 3. Project APIs

- [x] 3.1 In `backend/api.py`, add `GET /projects` and `GET /projects/{slug}` (design decision 7):
  - visitors see published data only; staff also get drafts and the draft count;
  - an unknown slug, or a project with no published photo for a visitor, answers 404;
  - rate-limited like the other public reads.

  Keep `GET /projects/{folder}/spaces` unchanged. Verify with tests: visitor vs staff counts, site-photo order with `anh_trang`, and 404s.
- [x] 3.2 Add `PUT /projects/{slug}` for the lead architect and admin:
  - validation as in the spec, with `muc_dau_tu` checked against the taxonomy;
  - only the staff fields can be changed;
  - every change is logged in `nhat_ky_du_an` with `truoc` / `sau`.

  Verify with tests: a valid edit is logged; a bad investment level gives 422 and changes nothing; an architect gets 403; an unknown slug gives 404.

## 4. Consumers

- [x] 4.1 `pipeline/project_stats.py`:
  - group by `du_an_slug` and fall back to the folder for spaces with none;
  - add the project name;
  - leads match `ngu_canh->>'du_an' = du_an_slug`.

  Update `weekly_report.py` names the same way. Verify: the existing `test_project_*` tests pass after their fixtures set `du_an_slug`, plus a new test where a lead from `/du-an/<slug>` counts for a project stored in a differently named folder.
- [x] 4.2 `pipeline/project_results.py`: group by `du_an_slug`, with cards carrying `slug`, `ten` and `co_trang`, and the photo's `anh_trang`. Keep `folder` for the pending `assistant-project-results` 3.1. Verify: `backend/tests/test_project_results.py` passes, and a new case shows that two folders matched to one project produce one card.
- [x] 4.3 `pipeline/quiz.py` and the `/quiz/result` response: return up to 3 projects as the `style-quiz` delta specifies. Verify with a test: projects are ranked by the number of photos in the result's styles, then by distance; no eligible project gives an empty list; the suggested spaces are unchanged.

## 5. Run, verify, document

- [ ] 5.1 On Docker:
  1. Run `python sync_projects.py --dry-run` and check the borderline pairs. Adjust the threshold only if true pairs fall below it.
  2. Run the sync.
  3. Confirm that `GET /projects` lists the matched projects, `/quan-tri/hieu-qua` shows "Hanjadin Apartment" instead of `hanjadin`, and a published matched photo shows "Chi tiết không gian" in the `/du-an/hanjadin-apartment` Lightbox.

  Run the full `pytest` suite; only the known environment failures may remain.
- [x] 5.2 Update `TONG-QUAN-DU-AN.md`: UC02, UC06, BFD 5.4, roadmap 0.1, technical debt 9.1 and 14, the API table (the three routes), the table list (`du_an`, `nhat_ky_du_an`) and the script table (`sync_projects.py`).

## Workflow follow-up

- **Optional:** run `sync_projects.py --ingest --limit N` in batches when Gemini quota allows. Each unmatched site photo costs one call.
- **Frontend (Tùng):** `/du-an` and the project page can read `GET /projects` / `GET /projects/{slug}` and show the project details, and the static build keeps `projects.js`.
