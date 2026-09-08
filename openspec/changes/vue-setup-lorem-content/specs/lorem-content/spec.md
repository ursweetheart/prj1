## ADDED Requirements

### Requirement: Replace hero section text with lorem ipsum
The hero section text (eyebrow, h1 heading, lead paragraph) SHALL be replaced with lorem ipsum of equivalent length.

#### Scenario: Hero heading on HomeView
- **WHEN** the HomeView renders the hero section
- **THEN** the `h-hero` heading displays a lorem ipsum phrase (~6-8 words), the eyebrow shows ~3 lorem words, and the lead paragraph shows ~2-3 sentences of lorem ipsum

### Requirement: Replace magazine section text with lorem ipsum
The magazine-style section (eyebrow, h2, body paragraphs) SHALL use lorem ipsum content.

#### Scenario: Magazine section on HomeView
- **WHEN** the HomeView renders the `.mag` section
- **THEN** the eyebrow, heading, and body paragraphs contain lorem ipsum text of similar length to the original Vietnamese text

### Requirement: Replace project data text with lorem ipsum
All text fields in the PROJECTS and SPACES data (`brief`, `note`, `space` name, `projectName`) SHALL be replaced with lorem ipsum.

#### Scenario: Space card displays lorem ipsum
- **WHEN** a SpaceCard component renders a space from the data
- **THEN** the project name and space name are lorem ipsum phrases, and the brief/note fields contain lorem ipsum paragraphs

### Requirement: Replace CTA and panel text with lorem ipsum
Call-to-action panels and section headings throughout the site SHALL use lorem ipsum text.

#### Scenario: CTA panel on HomeView
- **WHEN** the bottom CTA panel renders
- **THEN** the heading and description paragraph display lorem ipsum text

### Requirement: Replace services and process text with lorem ipsum
The SERVICES and PROCESS data entries (name, desc fields) SHALL use lorem ipsum content.

#### Scenario: Services data
- **WHEN** a component accesses SERVICES data
- **THEN** each service `name` is a short lorem ipsum phrase and each `desc` is a lorem ipsum sentence

### Requirement: Preserve UI labels and navigation text
Navigation items, filter labels, button text, facet names, and functional UI labels SHALL NOT be replaced with lorem ipsum.

#### Scenario: Navigation stays functional
- **WHEN** the SiteNav renders
- **THEN** navigation labels remain as-is (e.g., "Công trình", "Dịch vụ") or are replaced with equivalent functional text, NOT lorem ipsum

#### Scenario: Filter labels stay meaningful
- **WHEN** the FacetPanel renders
- **THEN** facet group labels (e.g., "Loại công trình", "Phong cách") and option labels (e.g., "Chung cư", "Modern") remain unchanged — these are functional taxonomy, not content

### Requirement: Preserve data structure integrity
The structure of FACETS, PROJECTS, SPACES arrays and all field keys SHALL remain identical — only string values for content fields change.

#### Scenario: Filtering still works
- **WHEN** user selects a filter option on CongTrinhView
- **THEN** the filtering logic works correctly because facet IDs, field keys, and array structure are unchanged
