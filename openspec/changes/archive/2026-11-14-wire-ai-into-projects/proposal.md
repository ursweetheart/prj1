## Why

The backend (ursweetheart, merged 2026-11-02) reads each photo: furniture hotspots, palette, materials, caption, taxonomy tags, text and photo search, similar spaces. None of it shows on the new site: project pages read 64 static folders from `src/assets/projects/`, the AI works on "spaces" in Postgres, and `/cong-trinh` (the only search page) redirects to `/du-an`.

The site is a catalog: project pages must stay pure photos and text. The AI is a separate tool for one purpose — finding similar spaces — not a sales layer. (User decisions, 2026-11-13.)

## What Changes

- **Projects stay pure.** `/du-an` and `/du-an/<slug>` keep their look. The Lightbox only gains a small "Chi tiết không gian →" link for photos that have a published space, and `?anh=<file>` opens the Lightbox on one photo.
- **New menu item "Không gian"** (hidden without backend):
  - `/khong-gian`: search by description, "Tìm bằng ảnh", taxonomy filters; results are photos in the project-grid style. `/cong-trinh` redirects here.
  - `/khong-gian/:id`: one photo large with object hotspots (name only, link to similar spaces), caption, materials, palette, similar spaces, "← <project> · ảnh n" back to the project, ‹ › through the project's other published photos. Same visual language as the project page.
- **Home band** between the project grid and the CTA: "Có một không gian bạn thích? Tìm không gian tương tự…" with "Tìm bằng ảnh" and "Mô tả bằng lời →"; hidden without backend.
- **Search variety:** text search returns at most 2 photos per project, like photo search already does.
- **Backend sync:** `ingest_projects.py` puts the project photos into `image_d3/<slug with _>/`; `GET /projects/{folder}/spaces` returns one project's published spaces. Publishing stays manual in `/quan-tri`.

## Non-goals

- Sales actions on hotspots (prices, chat about an item).
- Changing AI models, review states or admin pages.
- English translations of AI text.

## Capabilities

### New Capabilities
- `space-explorer`: the "Không gian" section — search page, space page, menu item and home band, all hidden without a backend.
- `project-space-link`: the small link from a project photo to its space, and the `?anh=` deep link back.
- `project-space-sync`: slug ↔ folder mapping, ingest command, per-project spaces endpoint, per-project cap on text search.

### Modified Capabilities
- (none archived under `openspec/specs/`)

## Impact

- Frontend: `src/router/index.js`, `src/components/SiteNav.vue`, `src/App.vue`, `src/views/HomeView.vue`, `src/views/ProjectView.vue`, `src/components/Lightbox.vue`, `src/views/CongTrinhView.vue` → `SpacesView.vue`, `src/views/SpaceView.vue`, `src/components/HotspotImage.vue`, new `src/components/SpaceTile.vue`, `src/components/SpaceSearchBand.vue`, `src/lib/projectSpaces.js`, `src/api.js`, `src/assets/app.css`.
- Backend: `backend/api.py`, `backend/pipeline/search.py`, new `backend/ingest_projects.py`, tests.
- Data: ~626 photos copied into `backend/image_d3/` (git-ignored) and processed once on CPU.
- Running AI features needs the backend on `:8001` plus `backend/.env` and `sa-key.json` from ursweetheart.
