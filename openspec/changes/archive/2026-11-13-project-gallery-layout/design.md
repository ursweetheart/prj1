## Context

- Current page: two-column grid (340px info | viewer), viewer is a 4:3 box with `object-fit: contain`, one photo at a time.
- Photos come from `src/assets/projects/<slug>/` via `import.meta.glob` (URLs only, no dimensions).
- Sample project 01: 9 photos, 2048 px wide, ratios 1.40 (×4), 1.00 (×3), 0.80 (×2).
- Reference (elemental.com.vn/portfolio/…): right-hand stack where landscape photos fill the width and portrait photos sit two per row at equal height, ~12 px gaps, all at natural ratio.

## Goals / Non-Goals

**Goals:** every photo visible at its true ratio; professional rhythm; no dead space; no layout shift; still "drop files in a folder".

**Non-Goals:** compression, captions, per-photo ordering UI.

## Decisions

### 1. Dimensions at build time via a Vite plugin
`vite-plugins/projectImageSizes.js` provides the virtual module `virtual:project-image-sizes` → `{ "<slug>/<file>": [w, h], "<file>": [w, h] }` for every image under `src/assets/projects/`. It reads only the file header (JPEG SOF marker, PNG IHDR, WebP VP8/VP8L/VP8X) — no dependency. In dev it watches the folder and, on add/unlink/change, invalidates the virtual module and triggers a full reload.
*Alternatives:* measuring in the browser after load (layout jumps, defeats lazy loading); a `npm run` manifest script (must be re-run after every new photo).

### 2. Row grouping: pure function `galleryRows(images)`
`src/lib/galleryRows.js`, unit-tested with Vitest. Input `[{ src, w, h }]` in folder order; output rows `[{ items, lone }]`:
- ratio `w/h ≥ 1.25` → its own row;
- otherwise collect consecutive non-landscape photos two at a time into one row;
- a non-landscape photo left alone → its own row with `lone: true`.
Order is preserved, so the editor controls the rhythm through file names.

### 3. Equal-height rows without cropping (CSS)
Each row is `display: flex; gap: G`. Each item gets `flex: <w/h> 1 0%` and the `<img>` is `width: 100%; height: auto` with `width`/`height` attributes. With flex-basis 0 and grow ∝ ratio, every item in a row ends up exactly `(rowWidth − gaps) / Σratio` tall → equal heights, full row width, natural ratio. Lone portrait/square rows: centred, `max-width: min(66%, 72vh × ratio)` so they never exceed about one screen in height. Gap `clamp(8px, 1vw, 14px)` between items and rows.
Below 600 px: everything is one photo per row, full width (pairs would be too small).

### 4. Page structure
```
[type eyebrow]
Dự án mẫu 01                         [description, when present]
───────────────────────────────────────────────────────────────
[ landscape ...................................................]
[ landscape ...................................................]
[ square ........................ ][ portrait .................]
[ portrait ...................... ][ square ...................]
          [ square (alone, centred) ]
[ landscape ...................................................]
───────────────────────────────────────────────────────────────
← Dự án trước            Tất cả dự án            Dự án tiếp →
```
- Container widened to 1280px for the gallery (title row and nav use the same edges).
- Title row: flex, space-between, wraps on small screens; no left column, so no empty space.
- Images: first two `loading="eager"`, others lazy, `decoding="async"`, `alt` = `<name> — ảnh <i>`.
- Each photo is a `<button>` that opens `Lightbox` at that index (← → / Esc already supported); hover: slight brighten like the grid cards.

### 5. Data
`projects.js` builds `images: [{ src, w, h }]` from the folder (falls back to the cover with its own size). `cover` stays a URL string for the home grid.

## Risks / Trade-offs

- Photos are 2.5–3.6 MB each (~27 MB for project 01) → lazy loading limits the first load, but compressing to ~2000 px / ≤ 600 KB is strongly recommended before going live.
- EXIF-rotated JPEGs would report swapped sizes → not the case for the current Behance exports; noted for later.
- A plugin adds build complexity → ~60 lines, no dependency, isolated in `vite-plugins/`.
