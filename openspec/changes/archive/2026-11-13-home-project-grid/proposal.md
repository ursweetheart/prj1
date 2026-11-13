## Why

The client's references ask for a minimal home page: Elemental (elemental.com.vn) shows little more than a strip of projects under a short intro, with small type filters and a "Show more" button. Below the hero, the D3 home page currently stacks five sections ("Bốn không gian mới", "Cách tìm cảm hứng", "Hai nhóm công trình", "Tất cả không gian", CTA), shows *spaces* instead of *projects*, repeats the same photos twice, and its space cards have broken images.

## What Changes

- Replace everything between the hero and the CTA with one **project grid** laid out like Elemental:
  - heading "Dự án" + one short intro sentence;
  - type filter tabs: **Tất cả · Nhà ở · Thương mại** (replaces the "Hai nhóm công trình" section);
  - masonry of **one card per project**: cover photo at its natural aspect ratio, project name, one small line (type · year);
  - "Xem thêm" button when there are more than 9 projects.
- **Remove** the sections "Bốn không gian mới", "Cách tìm cảm hứng", "Hai nhóm công trình" and "Tất cả không gian" from the home page.
- New home project list `src/data/homeProjects.js` with **temporary placeholder projects** using the 5 photos the user added (covers in `src/assets/projects/`); real names and photos come later from the studio's Behance.
- Keep the CTA, shortened to one sentence and the existing buttons.

## Non-goals

- Project detail page (reference: ahl.vn project page) — later change; cards are not links yet.
- Warm "scarlet" colour tone (reference: kimfurniture.com The Scarlet) — separate change `warm-scarlet-tone`.
- `/cong-trinh` keeps its space-based browsing and filters.
- Fixing the CTA's `/lien-he` link (route does not exist yet).

## Capabilities

### New Capabilities
- `home-project-grid`: minimal, filterable project strip on the home page.

## Impact

- `src/views/HomeView.vue` (sections removed, grid added), new `src/components/ProjectGrid.vue`, new `src/data/homeProjects.js`, new folder `src/assets/projects/`, `src/assets/app.css` (grid, tabs, card rules).
- The home page no longer calls `usePortfolio()`.
