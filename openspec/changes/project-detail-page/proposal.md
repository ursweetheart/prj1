## Why

On the home project grid only the image reacts to the mouse; the name is plain text (visitors end up selecting it) and nothing opens on click. The user expects each project to be one card: the whole card lights up on hover and opens the project. There is no project page yet; the client's reference for it is ahl.vn (short info table + one paragraph + photo viewer, all on one screen).

## What Changes

- **Whole card is a link** to `/du-an/<slug>`: image, name and meta line in one `router-link`. Hover / keyboard focus: image brightens slightly and zooms 2%, name lifts and glows like the top bar, meta line brightens. Text is no longer selectable by accident.
- **New project page** `/du-an/:slug` (AHL style):
  - left column: building type, project name, short description when available (no info table — user decision 2026-11-01);
  - right: photo viewer with crossfade, ‹ › arrows, counter "1 / n", ← → keys; arrows hidden for a single photo;
  - bottom: "← Dự án trước · Dự án tiếp →" and "Tất cả dự án";
  - unknown slug: short "Không tìm thấy dự án" message with a link home;
  - top padding so the fixed header does not cover the content.
- Project data moves from `src/data/homeProjects.js` to `src/data/projects.js` and gains optional fields `brief` and `images`.

## Non-goals

- Clicking a hero photo to open its project (later; needs a caption target).
- Real project content (comes from the studio's Behance) and admin editing (later, backend).
- Linking a project's spaces from `/cong-trinh`.

## Capabilities

### New Capabilities
- `project-detail-page`: AHL-style page for one project, reached from the home grid.

### Modified Capabilities
- `home-project-grid` (change not archived yet): cards become links with a top-bar-style hover.

## Impact

- New `src/views/ProjectView.vue`, route in `src/router/index.js`, `src/components/ProjectGrid.vue`, `src/data/projects.js` (renamed from `homeProjects.js`), `src/assets/app.css`.
