## MODIFIED Requirements

### Requirement: Ingest An Uploaded Image
The system SHALL accept an uploaded jpg, jpeg, png or webp image with an optional project name, run the processing pipeline, store the result as a `draft` space and return it. The image SHALL be stored in a folder named after the project, folded to lower-case ASCII letters, digits and underscores; without a usable project name it SHALL be stored in the upload folder.

#### Scenario: Valid image
- **WHEN** a jpg image is uploaded
- **THEN** the response is 201 with the stored space including AI facets, caption and `review_status` `draft`
- **AND** the image is retrievable under `/images/`

#### Scenario: Image with a project name
- **WHEN** an image is uploaded with project `Biệt thự Thảo Điền`
- **THEN** it is stored as `biet_thu_thao_dien/<file name>` and that folder is the space's project

#### Scenario: Project name cannot escape the image folder
- **WHEN** the project name is `../../etc`
- **THEN** the image is stored under `etc/` inside the image folder

#### Scenario: Unsupported file
- **WHEN** a non-image file is uploaded
- **THEN** the response is 415 and nothing is stored

#### Scenario: Path components in file name
- **WHEN** the uploaded file name contains directory components
- **THEN** the file is stored under the project or upload folder using only its base name

### Requirement: Human Review Workflow
The system SHALL let a reviewer correct a space's `space_type`, `design_style`, `caption`, `alt_text` and `materials` and advance its `review_status` strictly in the order `draft`, `in_review`, `approved`, `cleared`, `published`, one step per request. Architects MAY move `draft` to `in_review`; only `lead_architect` or `admin` SHALL approve, clear and publish. Moving to `cleared` SHALL require an explicit confirmation that the client allowed the photos to be published. Every edit and every advance SHALL be written to the review log. AI output SHALL NOT publish a space automatically.

#### Scenario: Confirm and edit
- **WHEN** a draft space is patched with `advance=true` and `design_style=Japandi`
- **THEN** its status becomes `in_review` and its style `Japandi`

#### Scenario: Edit AI text and materials
- **WHEN** a space is patched with a new `caption` and `materials` `["gỗ óc chó"]`
- **THEN** both are stored, the review log records the old and new values
- **AND** the space's `vat_lieu` tags become `go` only

#### Scenario: Invalid facet value
- **WHEN** a patch contains a `space_type` or `design_style` outside the allowed taxonomy
- **THEN** the response is 422 and the space is unchanged

#### Scenario: Clearing needs the rights confirmation
- **WHEN** an `approved` space is advanced without `rights_confirmed=true`
- **THEN** the response is 422 and the space stays `approved`

#### Scenario: Cleared then published
- **WHEN** an `approved` space is advanced with `rights_confirmed=true`, then advanced again
- **THEN** it becomes `cleared`, then `published`

#### Scenario: Architect cannot clear
- **WHEN** an `architect` advances an `approved` space
- **THEN** the response is 403

#### Scenario: Past the final state
- **WHEN** a `published` space is advanced
- **THEN** the response is 409

## ADDED Requirements

### Requirement: Content Editors Edit Text Only
The system SHALL let the `content` role edit `caption` and `alt_text` of a space in `in_review` and SHALL refuse with 403 any other change by that role, including facet edits, advancing, and edits in other states.

#### Scenario: Content edits the caption in review
- **WHEN** a `content` user patches the `caption` of an `in_review` space
- **THEN** the caption is updated

#### Scenario: Content cannot advance or edit facets
- **WHEN** a `content` user patches `advance=true` or `design_style`
- **THEN** the response is 403 and the space is unchanged

#### Scenario: Content cannot edit a draft
- **WHEN** a `content` user patches the `caption` of a `draft` space
- **THEN** the response is 403

### Requirement: Human Tags On Spaces
The system SHALL let staff set the values of one human-filled taxonomy dimension on a list of spaces or on every space of a project, replacing that dimension's human tags on those spaces. It SHALL refuse with 422 a dimension mirrored from AI columns (`khong_gian`, `phong_cach`, `tong_mau`, `vat_lieu`), a value not in the dimension, or more than one value for a single-value dimension.

#### Scenario: Tag a whole project
- **WHEN** staff set `loai_cong_trinh` = `biet_thu` for project `indochine_chinosere_villa`
- **THEN** every space in that folder carries `loai_cong_trinh: ["biet_thu"]` with source `nguoi`

#### Scenario: Replace a previous value
- **WHEN** staff later set `loai_cong_trinh` = `nha_pho` on the same spaces
- **THEN** they carry only `nha_pho` for that dimension

#### Scenario: AI dimension refused
- **WHEN** staff try to set `phong_cach` through this endpoint
- **THEN** the response is 422

#### Scenario: Unknown value refused
- **WHEN** staff set `muc_dau_tu` = `free`
- **THEN** the response is 422 and no tag changes

### Requirement: Confirm Detected Hotspots
The system SHALL let staff keep a subset of a space's detected objects, identified by their index, optionally renaming each kept object's Vietnamese label; objects not kept SHALL be removed. Coordinates and boxes SHALL stay as detected.

#### Scenario: Remove and rename
- **WHEN** a space with 3 detected objects is patched with hotspots `[{index: 2, label_vi: "Kệ TV gỗ óc chó"}]`
- **THEN** it has one object, the former third, with that label and its original anchor

#### Scenario: Unknown index
- **WHEN** the keep-list names an index that does not exist
- **THEN** the response is 422 and the hotspots are unchanged

### Requirement: Bulk Advance
The system SHALL advance several spaces one step in one request, applying the single-advance rules to each, and SHALL change none of them if any one fails, naming the failing space.

#### Scenario: Advance a selection
- **WHEN** staff advance three `draft` spaces together
- **THEN** all three become `in_review` and each advance is logged

#### Scenario: One space cannot move
- **WHEN** a selection contains a `published` space
- **THEN** the response is 409 naming that space and no space changes state
