## Context

- Projects: `src/data/projects.js` → `PROJECTS_LIST` from `src/assets/projects/<slug>/` (64 projects, ~626 photos). `ProjectView` = gallery + generic `Lightbox` (`items: {img, alt}`, bar with counter + "Đóng").
- Partner pages already holding the AI: `CongTrinhView` (text/photo search, `FacetPanel`, `useBrowse`, drawer, `usePortfolio` with demo fallback) and `SpaceView` (`HotspotImage`, `PaletteRow`, similar via `SpaceCard`). Both use the older light-card look (`.mosaic`, `.pcard`) instead of the project-grid look.
- Backend: one `space` row per photo, `relative_path = <folder>/<file>`, `subfolder` = folder. `save_records` upserts and would overwrite staff edits. `by_image` already caps 2 per project; `by_text` does not.

## Goals / Non-Goals

**Goals:** project pages unchanged except one link; AI section reuses partner logic with the new visual language; nothing AI renders (and no visible error) without a backend.

**Non-Goals:** new AI capabilities, admin UI, sales features on hotspots.

## Decisions

1. **Slug ↔ folder by `-` ↔ `_`** in `src/lib/projectSpaces.js` (`folderOf`, `slugOf`, `fileOf`). `project_folder()` already yields `[a-z0-9_]`, slugs are `[a-z0-9-]`, so it is lossless. No lookup table.

2. **Availability probe.** `aiAvailable()` = memoised `GET /taxonomy` with a 4 s timeout, reactive `ai.state` (`unknown | on | off`). It always asks: the Docker build also has no `VITE_API_URL` (nginx proxies `/api`), so a missing variable does not mean no backend; on GitHub Pages `/api/taxonomy` is a fast 404. Nav, home band and the Lightbox link read it.

3. **Endpoint `GET /projects/{folder}/spaces`** filters `split_part(relative_path,'/',1) = folder` (not `LIKE`: `_` is a wildcard), order by `relative_path`, light fields only (no palette/hotspots: the Lightbox link and ‹ › only need ids and paths). Used by ProjectView (link) and SpaceView (‹ ›). Alternative `GET /spaces?project=` rejected: that endpoint is paged at 200 and returns tags.

4. **`ingest_projects.py [slug ...]`** reads `../src/assets/projects`, copies to `image_d3/<folder>/`, skips paths already in `space`, `process_image(dest, base_dir=IMG_DIR)` + `save_records` per photo (resumable). Never touches `review_status`.

5. **`by_text` per-project cap** mirrors `by_image`: fetch `4*MAX_K` rows with `subfolder`, keep ≤ `PER_PROJECT` per folder until k.

6. **Pages.** `CongTrinhView.vue` is renamed `SpacesView.vue` (git mv) and restyled; `/khong-gian` → it, `/cong-trinh` → redirect keeping hash, `/khong-gian/:id` → `SpaceView`. Results use a new `SpaceTile.vue` (project-grid card look: natural-ratio image in CSS columns, project name, space type) instead of `SpaceCard` (moodboard heart, square crop). When `usePortfolio` falls back to demo data the page shows the "needs server" note instead of demo cards.

7. **Space page layout** mirrors `.pv`: eyebrow (space type · style), title = project name, photo at natural ratio (hotspot overlay sized to the image box), info column (caption, materials, palette), "Không gian tương tự" grid of `SpaceTile`s with `id="tuong-tu"`. Back link `← <project> · ảnh n` and ‹ › from the project's published spaces.

8. **Hotspot card** loses "kind/price"; shows the Vietnamese name and a button "Không gian tương tự" that emits/scrolls to `#tuong-tu` (`scrollBehavior` ignores same-path hashes, so it scrolls itself).

9. **Lightbox** gets one optional named slot `bar` rendered before "Đóng"; ProjectView fills it with the link when `spacesByFile.get(file)` exists. `?anh=` handled in ProjectView with `router.replace`.

10. **Home band → photo search.** A file input cannot be opened programmatically after navigation, so the band holds the input itself; the picked `File` goes into a module-level `pendingPhoto` in `projectSpaces.js`, then `router.push('/khong-gian')`; SpacesView consumes it on mount. "Mô tả bằng lời" pushes `/khong-gian?tim=mo-ta` and the page focuses the field.

## Risks / Trade-offs

- [CPU ingest of 626 photos is slow] → per-slug runs, resumable by skip-existing.
- [Wrong detections] → staff prune hotspots in `/quan-tri` before publishing; only published spaces show.
- [Published list capped at 200 for filters] → `listPublished` pages with `offset` until a short page.
- [One probe request on every page load] → memoised per session, 4 s timeout, skipped on Pages.

## Migration Plan

Backend endpoint + ingest first, ingest a few projects, publish in `/quan-tri`, then the frontend. Rollback: revert frontend; the endpoint and extra spaces are harmless.
