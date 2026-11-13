# home-project-grid Specification

## Purpose
TBD - created by archiving change home-project-grid. Update Purpose after archive.

## Requirements

### Requirement: One project strip below the hero
Below the hero, the home page SHALL show a single project section — heading "Dự án", a one-sentence intro, type filter tabs and a grid of project cards — followed only by the CTA and the footer. The sections "Bốn không gian mới", "Cách tìm cảm hứng", "Hai nhóm công trình" and "Tất cả không gian" SHALL NOT be shown on the home page.

#### Scenario: Home page structure
- **WHEN** a visitor scrolls past the hero
- **THEN** they see the "Dự án" section with tabs and project cards, then the CTA, then the footer

### Requirement: One card per project, natural ratio
Each card SHALL represent one project and show its cover photo at the photo's natural aspect ratio, the project name and one meta line with the building type and year. Cards SHALL be laid out in 1, 2 or 3 columns at viewport widths below 600px, 600–1023px and 1024px and above.

#### Scenario: Desktop masonry
- **WHEN** the viewport is 1280px wide
- **THEN** the cards are in 3 columns and a portrait cover is taller than a landscape cover

#### Scenario: Phone
- **WHEN** the viewport is 390px wide
- **THEN** the cards are in one column and the page has no horizontal scroll

### Requirement: Filter by building type
The section SHALL offer the tabs "Tất cả", "Nhà ở" and "Thương mại". Selecting a tab SHALL show only the projects of that group, mark the tab as pressed and store the choice in the URL hash. Tabs that would show no project SHALL be hidden.

#### Scenario: Residential only
- **WHEN** the visitor selects "Nhà ở"
- **THEN** only apartment, townhouse and villa projects are shown and the URL ends with `#loai=nha-o`

#### Scenario: Reload keeps the filter
- **WHEN** the visitor reloads the page with `#loai=thuong-mai`
- **THEN** the "Thương mại" tab is selected and only commercial projects are shown

### Requirement: Show more
The grid SHALL show at most 9 projects at first and a "Xem thêm" button that reveals 9 more. The button SHALL be hidden when all matching projects are shown.

#### Scenario: Few projects
- **WHEN** 5 projects match the filter
- **THEN** all 5 are shown and there is no "Xem thêm" button

### Requirement: Editable project list
The home projects SHALL come from one data file listing name, type, year and cover per project, so real projects can replace the placeholders without changing components.

#### Scenario: Replacing a placeholder
- **WHEN** an editor changes a project's name and cover file in the data file
- **THEN** the home grid shows the new name and photo
