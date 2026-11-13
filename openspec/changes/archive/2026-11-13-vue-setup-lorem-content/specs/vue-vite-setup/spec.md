## ADDED Requirements

### Requirement: Vite project initialization
The system SHALL be initialized as a Vue 3 + Vite project with `package.json`, `vite.config.js`, and proper dev server configuration.

#### Scenario: Fresh npm install and dev server
- **WHEN** user runs `npm install` followed by `npm run dev`
- **THEN** the Vite dev server starts with HMR enabled and the site is accessible at `localhost:5173`

### Requirement: Single-File Components
All existing Vue components (SiteNav, SiteFoot, SpaceCard, FacetPanel, Lightbox, BeforeAfter, HotspotImage, PaletteRow, BrandMark) SHALL be converted to `.vue` SFC files under `src/components/`.

#### Scenario: Component parity
- **WHEN** each SFC is rendered
- **THEN** it produces identical HTML structure and behavior as the original inline template + setup function from `components.js`

### Requirement: Vue Router multi-page navigation
The project SHALL use `vue-router@4` to handle navigation between pages (Home, Công trình) as a SPA with client-side routing.

#### Scenario: Navigate between pages
- **WHEN** user clicks a nav link (e.g., "Công trình")
- **THEN** the app navigates to the route without full page reload, and the correct view component is rendered

#### Scenario: Direct URL access
- **WHEN** user accesses a route directly (e.g., `/cong-trinh`)
- **THEN** the Vite dev server serves `index.html` and Vue Router renders the correct view

### Requirement: Data module port
The data layer (`FACETS`, `PROJECTS`, `SPACES`, `SPECS`, `SERVICES`, `PROCESS` and helper functions) SHALL be ported to an ES module at `src/data/index.js` with named exports.

#### Scenario: Data import in components
- **WHEN** a component imports from `@/data`
- **THEN** it receives the same data structures as the original `window.D3` global

### Requirement: Composables extraction
The moodboard store and `useBrowse()` composable SHALL be extracted into separate files under `src/composables/`.

#### Scenario: useBrowse composable
- **WHEN** `CongTrinhView.vue` calls `useBrowse()`
- **THEN** it returns reactive `selected`, `results`, `counts`, `activeChips`, and methods `toggle`, `clear`, `clearAll` with identical filtering behavior

#### Scenario: useMoodboard composable
- **WHEN** any component calls `useMoodboard()`
- **THEN** it returns `has(id)`, `toggle(id)`, and reactive `count` with localStorage persistence

### Requirement: CSS design system preserved
The complete CSS file (`app.css`) with all design tokens, utilities, and component styles SHALL be imported globally and remain unchanged.

#### Scenario: Visual parity
- **WHEN** the Vue app renders any page
- **THEN** the visual appearance (colors, typography, spacing, layout, grid) is identical to the original HTML prototype

### Requirement: Static assets served from public
All image files (logo.jpg, pic1-9.jpg) SHALL be placed in `public/img/` and referenced with `/img/` paths.

#### Scenario: Images load correctly
- **WHEN** the app renders image references like `/img/pic1.jpg`
- **THEN** the images display correctly without 404 errors
