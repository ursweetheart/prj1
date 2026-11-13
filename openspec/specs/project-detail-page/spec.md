# project-detail-page Specification

## Purpose
TBD - created by archiving change project-detail-page. Update Purpose after archive.

## Requirements

### Requirement: Project card is one link with top-bar hover
Each card in the home project grid SHALL be a single link to `/du-an/<slug>` covering the photo, the name and the meta line. On hover and keyboard focus the photo SHALL brighten slightly and the name SHALL lift 3px, turn white and glow, with the top-bar timing curve.

#### Scenario: Hover a card
- **WHEN** the visitor hovers anywhere on "Dự án mẫu 01"
- **THEN** its photo brightens and its name lifts and glows

#### Scenario: Open a project
- **WHEN** the visitor clicks the photo or the name of "Dự án mẫu 01"
- **THEN** the page `/du-an/du-an-mau-01` opens

### Requirement: Project page
The page `/du-an/<slug>` SHALL show, in this order: a title row with the building type and the project name (and the description beside it when the project has one), then the full photo gallery of the project, then a contact block "Tư vấn về dự án này" with the contact form for this project, then the links to the previous / next project and to all projects. There SHALL be no side column and no placeholder text. The fixed header SHALL NOT cover the title row.

#### Scenario: Desktop
- **WHEN** the visitor opens `/du-an/du-an-mau-01` at 1280px
- **THEN** the title row ("Chung cư" and the name) is fully visible below the header, and the gallery follows under it across the full content width

#### Scenario: No description yet
- **WHEN** a project has no description
- **THEN** nothing is shown beside the name (no placeholder text)

#### Scenario: No empty space under the title
- **WHEN** a project without description is opened at 1280px
- **THEN** the gallery starts directly below the title row, across the full content width

#### Scenario: Phone
- **WHEN** the same page is opened at 390px
- **THEN** the content is in one column and there is no horizontal scroll

#### Scenario: Ask about this project
- **WHEN** the visitor scrolls past the last photo of `/du-an/du-an-mau-01`
- **THEN** the "Tư vấn về dự án này" block with the contact form is shown before the previous / next links, and a lead sent from it carries project `du-an-mau-01`

### Requirement: Navigate between projects
The page SHALL link to the previous and next project in list order (wrapping) and to the project list on the home page.

#### Scenario: Next project
- **WHEN** the visitor clicks "Dự án tiếp" on the last project
- **THEN** the first project opens, scrolled to the top

### Requirement: Unknown project
An unknown slug SHALL show "Không tìm thấy dự án" with a link to the home page.

#### Scenario: Wrong address
- **WHEN** the visitor opens `/du-an/khong-co`
- **THEN** they see "Không tìm thấy dự án" and a link home

### Requirement: Full project gallery
The page SHALL show every photo of the project at its own aspect ratio, without cropping or bars. Landscape photos (width/height ≥ 1.25) SHALL take a full row. Consecutive portrait or square photos SHALL be shown two per row at equal height, filling the row width. A portrait or square photo without a partner SHALL be centred and not taller than about one screen. Below 600px every photo SHALL take a full row. The order SHALL follow the file names.

#### Scenario: Mixed photos
- **WHEN** project 01 with photos of ratio 1.40, 1.40, 1.00, 0.80, 0.80, 1.00, 1.00, 1.40, 1.40 is opened at 1280px
- **THEN** the rows are: 1.40 | 1.40 | 1.00 + 0.80 | 0.80 + 1.00 | 1.00 alone, centred | 1.40 | 1.40, and photos in the same row have the same height

#### Scenario: No layout jump
- **WHEN** the visitor scrolls and lazy photos load
- **THEN** the space for each photo was already reserved and content below does not move

### Requirement: Full-screen photo
Clicking a gallery photo SHALL open it full screen with previous / next navigation (buttons and ← →) and close with Esc or the close button.

#### Scenario: Open and browse
- **WHEN** the visitor clicks the third photo and presses →
- **THEN** the fourth photo is shown full screen, and Esc returns to the page

### Requirement: Photo sizes without manual input
Photo dimensions SHALL be read automatically from the image files when the site is built or served, so adding a photo to `src/assets/projects/<slug>/` needs no other step.

#### Scenario: Add a photo in development
- **WHEN** an editor adds `10-ban-cong.jpg` to the folder while the dev server runs
- **THEN** the page reloads and the new photo appears in the gallery at its correct ratio
