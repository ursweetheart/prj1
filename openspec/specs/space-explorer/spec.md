# space-explorer Specification

## Purpose

A separate "Không gian" section where visitors find spaces similar to what they have in mind (a description, a photo, or filters) across all D3 projects, and read one space in detail.

## Requirements

### Requirement: Only with a backend
The menu item "Không gian" and the home band SHALL appear only when the AI backend answers. Without it the site SHALL look as before this change. Opening `/khong-gian` directly without a backend SHALL show a short note that the feature needs the server, with a link to `/du-an`.

#### Scenario: Static site
- **WHEN** the site runs on GitHub Pages without a backend
- **THEN** the menu shows no "Không gian" and the home page shows no band

#### Scenario: Backend up
- **WHEN** the backend answers
- **THEN** the menu shows "Dự án · Không gian · …" and the band appears between the project grid and the CTA

### Requirement: Old URL
`/cong-trinh` SHALL redirect to `/khong-gian`, keeping any filter hash.

#### Scenario: Old link
- **WHEN** a visitor opens `/cong-trinh#phong_cach=Japandi`
- **THEN** `/khong-gian#phong_cach=Japandi` opens with that filter applied

### Requirement: Search page
`/khong-gian` SHALL offer a description field, "Tìm bằng ảnh" and taxonomy filters, and by default show all published spaces. Each result SHALL show the photo, the project name and the space type, and open `/khong-gian/<id>`.

#### Scenario: Text search
- **WHEN** the visitor searches "phòng ngủ ấm tông gỗ"
- **THEN** matching photos are shown with the count and the query, at most 2 per project

#### Scenario: Photo search
- **WHEN** the visitor uploads a living-room photo
- **THEN** its thumbnail and similar published photos are shown; the photo is not stored

#### Scenario: Backend rejects the photo
- **WHEN** the visitor uploads a 12 MB photo
- **THEN** "Ảnh quá lớn, tối đa 8 MB." is shown and "Xóa" restores the default view

#### Scenario: Filters
- **WHEN** the visitor selects style "Japandi" and tone "Ấm"
- **THEN** only photos with both tags remain, with removable chips and live counts

### Requirement: Space page
`/khong-gian/<id>` SHALL show the photo large at its natural ratio, the space type and project name, caption, material chips, palette and up to 8 similar spaces. Empty fields SHALL be omitted. Unknown or unpublished ids SHALL show "Không tìm thấy không gian".

#### Scenario: Published space
- **WHEN** the visitor opens a published space
- **THEN** photo, type, project, caption, materials, palette and similar spaces are shown

### Requirement: Object hotspots
On the space page each kept object SHALL have a "+" marker on the photo; activating it SHALL show only the object's Vietnamese name and a "Không gian tương tự" action that scrolls to the similar spaces. No price, service or chat action SHALL be shown.

#### Scenario: Open a marker
- **WHEN** the visitor clicks the marker on the sofa
- **THEN** a card shows "Sofa" and "Không gian tương tự"; choosing it scrolls to the similar spaces

### Requirement: Back to the project
The space page SHALL link to its project at that photo (`/du-an/<slug>?anh=<file>`) and offer ‹ › to the previous and next published photos of the same project, hidden when it has only one.

#### Scenario: Browse within the project
- **WHEN** the visitor presses › on photo 3 of "Beaumont lounge"
- **THEN** the next published space of that project opens

### Requirement: Home band
The band SHALL say "Có một không gian bạn thích?" with "Tìm bằng ảnh" and "Mô tả bằng lời →". Picking a photo SHALL open `/khong-gian` already searching with it; "Mô tả bằng lời" SHALL open `/khong-gian` with the description field focused.

#### Scenario: Photo from home
- **WHEN** the visitor picks a photo in the band
- **THEN** `/khong-gian` opens showing results for that photo
