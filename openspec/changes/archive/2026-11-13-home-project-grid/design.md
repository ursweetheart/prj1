## Context

- Home sections below the hero come from `usePortfolio()` *spaces* (one card per room). The API card (`toCard` in `src/api.js`) has no project type or slug, so projects cannot be reliably derived from it yet.
- Demo data (`src/data/index.js`) has Latin placeholder names; the user's 5 real photos are in `src/assets/hero/behance_*.jpg`. Real project names and photos exist on Behance and will be filled in later.
- References: Elemental (layout), AHL (amount of text per project, for the later detail page), Kim / The Scarlet (tone, separate change).

## Goals / Non-Goals

**Goals:** one calm project strip below the hero; one card per project; filter by building type; easy to replace placeholder data with real projects.

**Non-Goals:** project detail page, colour tone, backend integration.

## Decisions

### Data: a small curated list, not derived from spaces
`src/data/homeProjects.js` exports `HOME_PROJECTS = [{ slug, name, loai, year, cover }]` and `HOME_FILTERS`. Covers are imported from `src/assets/projects/<slug>.jpg`. A curated list keeps the home page independent of the space API (which lacks project type) and is the single file to edit when real Behance projects arrive. When the API gains projects, the list can be swapped for an API call without touching the component.

Placeholder data: 5 projects "Dự án mẫu 01–05", covers copied from the 5 `behance_*.jpg` photos in the hero folder (copies so that editing the hero folder never breaks the grid), types split between Nhà ở and Thương mại, marked clearly as placeholders in the file.

### Filters: building groups
`HOME_FILTERS = [{ id: 'all', label: 'Tất cả' }, { id: 'nha-o', label: 'Nhà ở', loai: ['chung-cu', 'nha-pho', 'villa'] }, { id: 'thuong-mai', label: 'Thương mại', loai: ['lounge', 'fnb', 'showroom', 'van-phong'] }]` — reuses the existing `loai` ids. Tabs are buttons with `aria-pressed`; the choice is kept in the URL hash (`#loai=nha-o`) so it survives reload and back. Tabs with no project are hidden.

### Layout: CSS columns masonry
`column-count` 1 / 2 / 3 at <600 / 600–1023 / ≥1024px with `break-inside: avoid` on cards; images `width: 100%; height: auto` so each keeps its natural ratio (Elemental style). Container narrower than the current wide wrap (max ≈ 1120px) with generous whitespace. CSS columns need no JS and reflow on filter; the trade-off is top-to-bottom order per column, acceptable for a gallery.

### Card
Image, name (light weight, slightly larger), one meta line `Nhà ở · 2025` in a faint colour. No heart button, no three-facet line. Subtle hover: image opacity .9 + 1.02 scale inside a clipping box. Not a link yet (no project page); the card is an `<article>` so the later change only wraps it in a `router-link`.

### Show more
First 9 matching projects, then "Xem thêm" adds 9. Hidden when everything is shown; resets on filter change.

### Removed sections
"Bốn không gian mới", "Cách tìm cảm hứng" (magazine), "Hai nhóm công trình", "Tất cả không gian". CSS for `.mag`, `.mosaic`, `.pcard` stays (used by `/cong-trinh` and other views).

## Risks / Trade-offs

- [Placeholder names in production] → file header comment + names that clearly read as placeholders.
- [Large covers, 1.4–3 MB each] → `loading="lazy"`, `decoding="async"`; recommend compressing to ≈1600px wide when real photos are added.
- [Same photos in hero and grid] → acceptable for the temporary data.
