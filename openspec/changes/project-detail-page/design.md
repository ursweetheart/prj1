## Context

- Home grid (`ProjectGrid.vue`) renders `<article class="project">` cards from `HOME_PROJECTS` (5 placeholders, one cover each).
- Top-bar hover values: lift 3px, white, `text-shadow 0 0 14px rgba(255,255,255,.55)`, 0.45s `cubic-bezier(0.22,1,0.36,1)`; also available as `.glow-hover`.
- The fixed header covers the top of pages without a hero (known issue); on ≥1024px it is 80–96px tall, stacked below 1024px (~150px).
- Reference ahl.vn project page: info table + one paragraph on the left, photo carousel on the right, prev/next arrows, everything within one screen.

## Decisions

### Card = one router-link
`<router-link class="project" :to="'/du-an/' + slug">` wraps image, name, meta. Hover/focus on the card drives the children: image `filter: brightness(1.08)` + `scale(1.02)`; name `translateY(-3px)`, white, text glow; meta to `--ink-2`. Same curve as the top bar. `focus-visible` mirrors hover. Reduced motion: no movement, brightness/glow only.

### Route and data
`/du-an/:slug` → `ProjectView.vue` (lazy). `src/data/projects.js` exports `PROJECTS_LIST` (renamed from `HOME_PROJECTS`), `PROJECT_FILTERS`, `LOAI_NAME`, `projectBySlug(slug)`. Optional fields per project: `address`, `area` (m²), `status`, `team`, `brief`, `images` (defaults to `[cover]`). The home grid imports from the new file. Renaming now avoids a "home" file that also feeds another page.

### Page layout (AHL)
```
≥ 1024px                                        < 1024px
┌──────────────┬─────────────────────────┐      name
│ Dự án mẫu 01 │                         │      photo viewer
│ Loại   ...   │   ‹    [ photo ]    ›    │      info table
│ Năm    ...   │                         │      description
│ Địa chỉ ...  │              1 / 3      │      prev / next
│ ...          │                         │
│ description  │                         │
└──────────────┴─────────────────────────┘
← Dự án trước          Tất cả dự án          Dự án tiếp →
```
- Container 1120px like the grid; left column 340px, gap 56px; photo box `aspect-ratio: 4/3`, `object-fit: contain` on a dark panel so any photo ratio fits within one screen (`max-height: 72vh`).
- Info table: label (faint, 12px uppercase) / value (ink-2); missing → "Đang cập nhật" in faint italic.
- Viewer: layered crossfade (same technique as the hero), arrow buttons with `.glow-hover`, counter, ← → keys when the viewer has focus.
- Prev/next project follow the list order, wrapping; links use `.glow-hover`.
- Page top padding: `clamp(150px, 18vw, 170px)` below 1024px, `128px` from 1024px, so the fixed header never covers the title.
- `document.title` = `<name> — D3 Studio`; scroll to top on slug change (router default keeps position, so set it explicitly).

### Not found
Unknown slug → name area shows "Không tìm thấy dự án" + "Về trang chủ" link; no viewer.

## Risks / Trade-offs

- Placeholder projects have one photo, so the viewer shows no arrows until real galleries are added → expected.
- "Đang cập nhật" rows are visible to the client → intentional for the prototype: shows what each project page will contain.

### Router scroll behaviour (added during apply)
The router had no `scrollBehavior`, so a new page kept the previous scroll position. Added globally in `src/router/index.js`: saved position on back/forward; no scroll when only the hash changes on the same path (filter tabs `#loai=...`); scroll to an element for id-like hashes (`/#du-an`, offset 110px for the fixed header); otherwise top of page.

### Header-safe top padding (measured)
Fixed header bottom: 165-168px at 360-390px, 186px at 600px, 200px at 768-1023px, 96px at >=1024px. Page padding-top: 196px / 232px from 600px / 128px from 1024px.

### Simplified left column (user decision)
The AHL-style info table was removed at the user's request: the page shows only the building type (eyebrow) and the name, plus the description once `brief` is filled in. No "Đang cập nhật" placeholders.
