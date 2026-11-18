# project-filter Specification

## Purpose
TBD - created by archiving change search-explanations. Update Purpose after archive.

## Requirements

### Requirement: Filter published projects by several dimensions
`GET /projects/filter` SHALL return the published projects matching every given filter (seq-10 steps 1-6, BFD 1.1):
- **style:** a value carried by at least one of the project's published photos;
- **building type:** the project's type or a `loai_cong_trinh` value on its photos;
- **area range:** in m², from the project's details;
- **investment level:** from the project's details.

Several values of one dimension SHALL mean any of them; different dimensions SHALL all apply. A project is published when it has at least one published photo. The answer SHALL include the total.

#### Scenario: Japandi apartments of 60-90 m²
- **WHEN** a visitor filters style Japandi, building type "Căn hộ" and area 60-90
- **THEN** only published projects with a Japandi photo, of that type and with an area from 60 to 90 m² are returned, with their number

### Requirement: Count per filter value
For each filter value, the answer SHALL give how many projects would match if that value were chosen together with the other dimensions' current choices (seq-10 step 5).

#### Scenario: Counts update
- **WHEN** style Japandi is chosen
- **THEN** each building type shows how many Japandi projects it has

### Requirement: Loosening suggestion
When no project matches, the answer SHALL suggest the single filter whose removal gives the most projects, with that number (seq-10 step 8).

#### Scenario: Nothing matches
- **WHEN** style Indochine, type "Văn phòng" and area 200-300 match nothing, and dropping the area gives 2 projects
- **THEN** the answer suggests "Bỏ lọc Diện tích: 2 dự án"

### Requirement: Sorting
Results SHALL be sortable by newest first (last publish date), largest area, and most viewed in the last 30 days (BFD 1.2). Newest SHALL be the default.

#### Scenario: Most viewed
- **WHEN** sorted by most viewed
- **THEN** the project whose photos were viewed most in the last 30 days is first

### Requirement: Ready-made filter component
A filter panel component SHALL use this API, show the counts, the loosening suggestion and the sort choice, and work by keyboard and at 360 px. Placing it on a page is left to that page's owner.

#### Scenario: Component in isolation
- **WHEN** the component is mounted with no filters
- **THEN** it lists every dimension's values with counts and emits the matching projects
