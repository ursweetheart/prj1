## 1. Data

- [x] 1.1 Rename `src/data/homeProjects.js` → `src/data/projects.js`; exports `PROJECTS_LIST`, `PROJECT_FILTERS`, `LOAI_NAME`, `projectBySlug`; document optional fields (`address`, `area`, `status`, `team`, `brief`, `images`)

## 2. Card as link

- [x] 2.1 `ProjectGrid.vue`: card becomes `router-link` to `/du-an/<slug>`; import from the new data file
- [x] 2.2 CSS: card hover/focus — photo brightens + 2% zoom, name lift + glow, meta brightens; reduced motion without movement

## 3. Project page

- [x] 3.1 Route `/du-an/:slug` → lazy `ProjectView.vue`
- [x] 3.2 `ProjectView.vue`: name, info table with "Đang cập nhật", description, prev/next/all links, not-found state, document title, scroll to top on slug change
- [x] 3.3 Photo viewer: layered crossfade, ‹ › buttons, counter, ← → keys, no buttons for one photo
- [x] 3.4 CSS: two columns from 1024px, stacked below, header-safe top padding, 1120px container

## 4. Verification

- [x] 4.1 Browser: card hover + click opens the page; page at 1280px and 390px; viewer with 1 and with several photos (temporary test data); prev/next wrap; unknown slug; no console errors
- [x] 4.2 `vite build` into a scratch directory succeeds; existing tests pass

## 5. Simplify (user request)

- [x] 5.1 Remove the info table and placeholder texts; left column = building type + name + description only when `brief` is set; drop `address`/`area`/`status`/`team` from the data docs
- [x] 5.2 One photo folder per project `src/assets/projects/<slug>/`, read with `import.meta.glob` and sorted by file name; empty folder falls back to the cover; README in `src/assets/projects/`
