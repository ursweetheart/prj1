## 1. Data

- [x] 1.1 Create `src/assets/projects/` and copy the 5 `behance_*.jpg` photos from `src/assets/hero/` as `du-an-mau-01.jpg` … `du-an-mau-05.jpg`
- [x] 1.2 `src/data/homeProjects.js`: `HOME_FILTERS` (Tất cả / Nhà ở / Thương mại) and `HOME_PROJECTS` with 5 placeholder projects (name, slug, loai, year, cover import), with a header comment explaining how to replace them

## 2. Component

- [x] 2.1 `src/components/ProjectGrid.vue`: heading "Dự án", intro sentence, filter tabs (`aria-pressed`, hidden when empty), URL hash `#loai=…` read on load and written on change
- [x] 2.2 Cards: cover at natural ratio (`loading="lazy"`, `decoding="async"`), name, meta line `<type> · <year>`
- [x] 2.3 Show the first 9, "Xem thêm" adds 9, reset on filter change, hidden when all shown
- [x] 2.4 Styles in `src/assets/app.css`: narrow container, tabs, CSS-columns masonry 1/2/3, card typography and hover

## 3. Home page

- [x] 3.1 `src/views/HomeView.vue`: remove "Bốn không gian mới", "Cách tìm cảm hứng", "Hai nhóm công trình", "Tất cả không gian" and the `usePortfolio` / `SpaceCard` imports; add `<ProjectGrid />`
- [x] 3.2 Shorten the CTA to one sentence + existing buttons

## 4. Verification

- [x] 4.1 Browser check at 390, 768, 1280px: column count, natural ratios, no horizontal scroll, tabs filter and hash, reload keeps filter, no console errors
- [x] 4.2 `vite build` into a scratch directory succeeds
