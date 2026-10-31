## ADDED Requirements

### Requirement: Bulk Project Upload
The review page SHALL let staff choose several images and a project name and upload them one request at a time, showing progress and listing each file that failed with its reason, without stopping the remaining uploads.

#### Scenario: Upload a project
- **WHEN** staff choose 5 images, enter project `Biệt thự Thảo Điền` and start the upload
- **THEN** the page shows progress up to 5/5 and the new spaces appear in the `Nháp` tab under that project

#### Scenario: One file fails
- **WHEN** the third of 5 files is rejected by the server
- **THEN** the other 4 are uploaded and the page names the third file and the error

### Requirement: Edit Space Content On The Review Page
The review page SHALL let staff edit a space's space type, style, caption, alt text and materials and save them, and SHALL show `content` users only the caption and alt text fields of spaces in review.

#### Scenario: Staff edits materials
- **WHEN** staff change the materials of a space and save
- **THEN** the change is sent to the API and kept after reloading

#### Scenario: Content user view
- **WHEN** a `content` user opens the `Chờ duyệt` tab
- **THEN** each space shows editable caption and alt text and no facet selects or advance buttons

### Requirement: Human Tags From The Review Page
The review page SHALL let staff set `loai_cong_trinh` and `muc_dau_tu` for one space or for every space of its project in one action.

#### Scenario: Apply to the whole project
- **WHEN** staff choose `Biệt thự` and "Áp cho cả dự án" on one space of a project
- **THEN** every space of that project is tagged `biet_thu`

### Requirement: Hotspot Confirmation On The Review Page
The review page SHALL show a space's detected objects on its image and let staff remove an object or rename its label, then save.

#### Scenario: Remove a wrong object
- **WHEN** staff remove a detected "tv" from a space and save
- **THEN** the space's detail page no longer shows that hotspot

### Requirement: Advance Spaces From The Review Page
The review page SHALL let staff select several spaces of the current status tab, or all spaces of a project, and advance them together; advancing to `Đã xác nhận quyền` SHALL require ticking a rights confirmation first. Buttons the user's role cannot use SHALL NOT be shown.

#### Scenario: Advance a project
- **WHEN** a lead architect selects all spaces of a project in the `Đã duyệt` tab, ticks the rights confirmation and advances
- **THEN** they move to the `Đã xác nhận quyền` tab

#### Scenario: Architect view
- **WHEN** an `architect` opens the `Đã duyệt` tab
- **THEN** no advance action is offered
