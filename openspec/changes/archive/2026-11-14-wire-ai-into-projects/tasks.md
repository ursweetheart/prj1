## 1. Backend: project ↔ space sync

- [x] 1.1 Add `GET /projects/{folder}/spaces` in `backend/api.py` (pattern `^[a-z0-9_]{1,60}$`, `split_part` match, published-only for visitors, ordered by path) with tests in `backend/tests/test_api.py` (visitor vs staff, unknown → [], invalid → 422); verify `python -m pytest tests/test_api.py` where a DB is available, else `python -c "import api"`
- [x] 1.2 Cap text search at 2 per project in `backend/pipeline/search.py` `by_text`, with a test in `backend/tests/test_search.py`; verify the module imports and the test file collects
- [x] 1.3 Add `backend/ingest_projects.py [slug ...]` (copy to `image_d3/<folder>/`, skip existing paths, never publish); verify `python ingest_projects.py --dry-run` lists 626 photos in 64 folders
- [x] 1.4 Document the command, slug→folder rule and manual publishing in `README.md`; verify the documented command matches the script's usage line

## 2. Frontend data layer

- [x] 2.1 Add `src/lib/projectSpaces.js` (`folderOf`, `slugOf`, `fileOf`, `ai` state + `aiAvailable()`, `loadProjectSpaces(slug)`, `pendingPhoto`) and `getProjectSpaces` in `src/api.js`, plus `listPublished` paging past 200; verify with `src/lib/projectSpaces.test.js` (`npm test`)

## 3. Không gian section

- [x] 3.1 Routes: `/khong-gian` (renamed `SpacesView.vue`), `/khong-gian/:id`, `/cong-trinh` redirect keeping hash; nav item "Không gian" only when `ai.state === 'on'`, active state in `App.vue`; verify in the browser with and without backend
- [x] 3.2 Add `SpaceTile.vue` (project-grid card look) and restyle `SpacesView.vue` to the new look (head like `/du-an`, search row, filters, tile columns, "needs server" note instead of demo data, `?tim=mo-ta` focus, `pendingPhoto` consume); verify `npm run build` and the page at 1440px / 390px
- [x] 3.3 Restyle `SpaceView.vue` like the project page (eyebrow, project title, natural-ratio photo with hotspots, info, similar `SpaceTile`s at `#tuong-tu`, back link with `?anh=`, ‹ › within project); hotspot card shows name + "Không gian tương tự" only; verify `npm run build`
- [x] 3.4 Add `SpaceSearchBand.vue` on the home page between grid and CTA, only when `ai.state === 'on'`; verify the home page without backend is unchanged

## 4. Project page link

- [x] 4.1 Lightbox `bar` slot; ProjectView loads the project's spaces and shows "Chi tiết không gian →" for published photos; `?anh=<file>` open/sync/close; verify `/du-an/<slug>?anh=03.jpg` opens photo 3 and `?anh=99.jpg` does not open, with backend stopped no link and no console error

## 5. Integration

- [x] 5.1 `npm test` and `npm run build` pass; with the backend stopped `/`, `/du-an`, `/du-an/<slug>` look as before and `/khong-gian` shows the note
- [x] 5.2 With the backend up: ingest 2–3 projects, publish them in `/quan-tri`, walk home band → `/khong-gian` → space → similar → project at that photo, at 1440px and 390px

## Workflow follow-up

- Archive with `/opsx:archive` after 5.2 is accepted.
