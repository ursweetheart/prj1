# Spec Delta

## MODIFIED Requirements

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
