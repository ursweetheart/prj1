## Why

The project page (`/du-an/<slug>`) shows one photo at a time inside a fixed 4:3 box: portrait and square photos get dark bars on both sides, visitors must click through 9 photos to see the project, and the left column is empty under the title. The user finds it amateurish. Reference studio sites (Elemental's project pages, Kim's The Scarlet) show **every photo of the project at its own aspect ratio** in a calm editorial sequence: landscape photos full width, portrait / square photos paired side by side at equal height, no cropping, no letterboxing.

## What Changes

- **Replace the single-photo viewer with a full editorial gallery** of all project photos:
  - landscape photos (ratio ≥ 1.25) take a full row;
  - consecutive portrait / square photos are paired in one row, scaled to the same height so the row is exactly full width (no crop, no bars);
  - a lone portrait / square photo is centred at a reduced width so it is never taller than a screen;
  - photos load lazily with their real width/height so the page does not jump.
- **No empty column**: the title block sits above the gallery as one compact row — building type + name on the left, description on the right when it exists.
- **Click a photo → full-screen viewer** (existing `Lightbox` component) with ← → and Esc.
- **Real photo sizes at build time**: a small Vite plugin reads the width/height of every image in `src/assets/projects/` (JPEG/PNG/WebP headers) and exposes them to the data module; adding or removing a photo in dev reloads the page.
- Keep: prev / next project links, "Tất cả dự án", not-found state, header-safe top padding, photo folders per project.

## Non-goals

- Image compression / responsive `srcset` (recommended separately: current photos are 2.5–3.6 MB each).
- Captions per photo.
- Hero / home grid changes.

## Capabilities

### Modified Capabilities
- `project-detail-page` (change not archived yet): the photo viewer requirement is replaced by the editorial gallery; the left info column is replaced by a title row.

## Impact

- `src/views/ProjectView.vue` (layout), new `src/lib/galleryRows.js` (+ unit test), `src/data/projects.js` (images carry `w`/`h`), `vite.config.js` (image-size plugin, new `vite-plugins/projectImageSizes.js`), `src/assets/app.css` (`.pv-*` rules rewritten).
