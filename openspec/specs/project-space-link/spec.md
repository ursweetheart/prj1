# project-space-link Specification

## Purpose

Keeps project pages pure photo galleries while letting a visitor step from one project photo to its AI detail page and back.

## Requirements

### Requirement: Small link in the Lightbox
In the Lightbox of `/du-an/<slug>`, a photo with a published space SHALL show one small text link "Chi tiết không gian →" in the top bar, opening `/khong-gian/<id>`. Nothing else SHALL be added on or around the photo. Photos without a published space, or any photo when the backend is unreachable, SHALL show no link and no error.

#### Scenario: Published photo
- **WHEN** the visitor opens a published photo in the Lightbox
- **THEN** "Chi tiết không gian →" is shown next to the counter

#### Scenario: Static site
- **WHEN** the backend is unreachable
- **THEN** the Lightbox looks exactly as before this change

### Requirement: Deep link to one photo
`/du-an/<slug>?anh=<file>` SHALL open the Lightbox on that photo. Moving in the Lightbox SHALL keep `anh` in sync without adding history entries; closing SHALL remove it. An unknown file SHALL leave the Lightbox closed.

#### Scenario: From a space page
- **WHEN** the visitor follows "← Beaumont lounge · ảnh 3" from a space page
- **THEN** `/du-an/beaumont-lounge?anh=03.jpg` opens with photo 3 in the Lightbox

#### Scenario: Unknown photo
- **WHEN** a visitor opens `/du-an/beaumont-lounge?anh=99.jpg`
- **THEN** the project page shows with the Lightbox closed
