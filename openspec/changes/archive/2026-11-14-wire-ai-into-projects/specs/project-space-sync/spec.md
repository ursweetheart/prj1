## Purpose

Connects the static project folders of the site with the spaces the AI backend analyses, so each project photo has exactly one space and the site can ask for a project's spaces in one call.

## ADDED Requirements

### Requirement: Project folder naming
A project photo `src/assets/projects/<slug>/<file>` SHALL correspond to the space whose relative path is `<folder>/<file>`, where `<folder>` is `<slug>` with every `-` replaced by `_`. The reverse mapping SHALL give the slug back.

#### Scenario: Map a slug
- **WHEN** the site looks up photo `01.jpg` of slug `beaumont-lounge`
- **THEN** it uses the space `beaumont_lounge/01.jpg`

### Requirement: Ingest project folders
A backend command SHALL copy every project photo into the backend image folder under its mapped folder and process it into a draft space. Photos already stored SHALL be skipped so staff edits are never overwritten. It SHALL accept slugs to process only those projects.

#### Scenario: Re-run
- **GIVEN** `apartment-in-grey` was ingested and `04.jpg` was added since
- **WHEN** the command runs again for that slug
- **THEN** only `apartment_in_grey/04.jpg` is processed

### Requirement: Publishing stays manual
The ingest command SHALL NOT publish spaces. Visitors SHALL see a space only after staff publish it in `/quan-tri`, including the rights confirmation.

#### Scenario: Freshly ingested
- **WHEN** a visitor opens a project right after ingest
- **THEN** its Lightbox shows no "Chi tiết không gian" link

### Requirement: Spaces of one project
`GET /projects/{folder}/spaces` SHALL return the spaces of that folder ordered by file name, with id, relative path, space type, style, materials, caption and alt text. Visitors SHALL get only published spaces; staff SHALL get all. An unknown folder SHALL return an empty list; a folder not matching `[a-z0-9_]{1,60}` SHALL get 422.

#### Scenario: Visitor
- **GIVEN** `beaumont_lounge` has 8 spaces, 5 published
- **WHEN** a visitor calls `GET /projects/beaumont_lounge/spaces`
- **THEN** 5 spaces are returned

#### Scenario: Invalid folder
- **WHEN** a client calls `GET /projects/Bad-Name/spaces`
- **THEN** the API answers 422

### Requirement: Varied text search
Text search SHALL return at most 2 spaces per project, filling the requested count from the next best matches.

#### Scenario: One project dominates
- **GIVEN** the 6 best matches for "lounge tối" are all from one project
- **WHEN** a visitor searches it with k=6
- **THEN** at most 2 results come from that project
