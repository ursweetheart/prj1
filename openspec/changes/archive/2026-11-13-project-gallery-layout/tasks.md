## 1. Photo sizes

- [x] 1.1 `vite-plugins/projectImageSizes.js`: virtual module with `[w, h]` for every image under `src/assets/projects/` (JPEG / PNG / WebP header parsing), dev watcher → invalidate + full reload; register in `vite.config.js`
- [x] 1.2 `src/data/projects.js`: `images: [{ src, w, h }]` from the folder, fallback to the cover with its size

## 2. Row layout

- [x] 2.1 `src/lib/galleryRows.js`: landscape alone, consecutive portrait/square paired, lone one marked `lone`
- [x] 2.2 `src/lib/galleryRows.test.js`: project-01 sequence, all landscape, odd count of portraits, empty list

## 3. Page

- [x] 3.1 `ProjectView.vue`: title row (type + name, description beside when present), gallery rows, each photo a button opening `Lightbox`; remove the old viewer
- [x] 3.2 CSS: 1280px container, title row, flex rows with `flex: ratio 1 0%`, lone photo centred and height-capped, one column below 600px, hover brighten; remove the old `.pv-grid` / viewer rules

## 4. Verification

- [x] 4.1 Browser at 1280px and 390px with the 9 photos of project 01: row grouping as in the spec, equal heights per row (±1px), no bars, no horizontal scroll, no layout shift while scrolling; Lightbox open / ← → / Esc; project without folder photos; console clean
- [x] 4.2 `vite build` into a scratch directory and `vitest run` pass

## 5. Found during verification

- [x] 5.1 Lightbox opened under the fixed header (z-index 80 < 100), hiding "Đóng": `.lb` raised to z-index 120 (fixes every page that uses `Lightbox`)
