## ADDED Requirements

### Requirement: Project card is one link with top-bar hover
Each card in the home project grid SHALL be a single link to `/du-an/<slug>` covering the photo, the name and the meta line. On hover and keyboard focus the photo SHALL brighten slightly and the name SHALL lift 3px, turn white and glow, with the top-bar timing curve.

#### Scenario: Hover a card
- **WHEN** the visitor hovers anywhere on "Dự án mẫu 01"
- **THEN** its photo brightens and its name lifts and glows

#### Scenario: Open a project
- **WHEN** the visitor clicks the photo or the name of "Dự án mẫu 01"
- **THEN** the page `/du-an/du-an-mau-01` opens

### Requirement: Project page
The page `/du-an/<slug>` SHALL show the building type above the project name, a short description only when the project has one, and a photo viewer. It SHALL NOT show an info table or placeholder text. On viewports 1024px and wider the type, name and description SHALL be in a left column beside the viewer; below that they SHALL stack with the viewer under the name. The fixed header SHALL NOT cover the building type or the project name.

#### Scenario: Desktop
- **WHEN** the visitor opens `/du-an/du-an-mau-01` at 1280px
- **THEN** "Chung cư" and the name are on the left, the photo on the right, and both are fully visible below the header

#### Scenario: No description yet
- **WHEN** a project has no description
- **THEN** nothing is shown under the name (no placeholder text)

#### Scenario: Phone
- **WHEN** the same page is opened at 390px
- **THEN** the content is in one column and there is no horizontal scroll

### Requirement: Photo viewer
The viewer SHALL show one photo at a time with a counter "i / n". With two or more photos it SHALL offer previous / next buttons and the ← → keys, crossfading between photos and wrapping around. With one photo it SHALL show no buttons.

#### Scenario: Single photo
- **WHEN** a project has only its cover photo
- **THEN** the viewer shows it with "1 / 1" and no arrows

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
