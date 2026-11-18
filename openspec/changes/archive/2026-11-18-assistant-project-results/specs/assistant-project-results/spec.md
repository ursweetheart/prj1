## Purpose

Show visitors whole projects as the assistant's examples, ranked by how much of their request each project matches, so they see where the studio has done what they want rather than scattered photos.

## ADDED Requirements

### Requirement: Examples Grouped by Project
When an answer shows examples, the assistant SHALL group matching published photos by project and return at most 3 projects, each with its 1 to 2 best photos. A project SHALL appear at most once. Unpublished photos SHALL never be used.

#### Scenario: Several photos of one project
- **WHEN** the five best-matching photos for a question come from two projects
- **THEN** the answer shows two project cards, not five photos

#### Scenario: Drafts never shown
- **WHEN** a project's best-matching photo is a draft
- **THEN** that photo is not on any card, and the project appears only if it has a matching published photo

### Requirement: Projects Ranked by Matched Constraints
Projects SHALL be ranked first by how many of the visitor's collected constraints (style, room type, building type) they match, where a constraint counts when at least one of the project's published photos has it; then by their best photo's similarity to the question; then by their number of matching photos. Each card SHALL state which constraints it matches.

#### Scenario: More factors first
- **WHEN** a visitor asked for a Japandi living room in an apartment, project A has Japandi living-room photos tagged apartment, and project B has a Japandi bedroom in a villa with a slightly more similar photo
- **THEN** A is listed before B, and A's card shows "Japandi · phòng khách · chung cư"

#### Scenario: No constraints
- **WHEN** the visitor gave no style, room or building type
- **THEN** projects are ranked by similarity alone and the cards show no matched-constraint line

### Requirement: Project Card Opens the Project
A card SHALL open the project's page on its best photo when the project has a page, and otherwise the best photo's space page.

#### Scenario: Project with a page
- **WHEN** a card's catalog project has a page and its best photo is one of that page's photos (see `project-catalog`)
- **THEN** the card opens `/du-an/<slug>?anh=<best photo file>`

#### Scenario: Project without a page
- **WHEN** a card's project exists only as photos in the database
- **THEN** the card opens `/khong-gian/<best photo id>`

### Requirement: Answers from Photo Descriptions Keep the AI's Choice
When an answer is written from photo descriptions, the cards SHALL be built from the photos the answer used, grouped by project in the order the photos were used, without adding photos the answer did not use.

#### Scenario: Answer used two photos of one project
- **WHEN** the AI's answer cites two photos from the same project
- **THEN** one card shows that project with those two photos
