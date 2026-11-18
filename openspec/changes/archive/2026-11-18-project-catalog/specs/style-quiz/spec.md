# Spec Delta

## ADDED Requirements

### Requirement: Suggested projects
With the result the server SHALL return up to 3 catalog projects with published photos of the result's styles, ranked by how many of their published photos have those styles and then by how close their best photo is to the photos the visitor chose. Each SHALL carry its slug, name, whether it has a page, the matched style and one photo. With no such project the list SHALL be empty.

#### Scenario: Projects follow the result
- **WHEN** the result is Indochine and Japandi, and two projects have published Indochine photos
- **THEN** those two projects are returned, the one with more Indochine photos first, each with one of its Indochine photos

#### Scenario: Nothing published yet
- **WHEN** no project has a published photo of the result's styles
- **THEN** the result has an empty project list and the suggested spaces are unchanged
