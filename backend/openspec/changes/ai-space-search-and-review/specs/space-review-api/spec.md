## ADDED Requirements

### Requirement: Browse Spaces
The system SHALL expose HTTP endpoints to list spaces with optional filters on `space_type`, `design_style` and `review_status` plus pagination, and to read one space including its palette and hotspots.

#### Scenario: Filtered list
- **WHEN** the list is requested with `space_type=phong_khach`
- **THEN** only living-room spaces are returned

#### Scenario: Missing space
- **WHEN** a space id that does not exist is requested
- **THEN** the response is 404

### Requirement: Ingest An Uploaded Image
The system SHALL accept an uploaded jpg, jpeg, png or webp image, run the processing pipeline, store the result as a `draft` space and return it.

#### Scenario: Valid image
- **WHEN** a jpg image is uploaded
- **THEN** the response is 201 with the stored space including AI facets, caption and `review_status` `draft`
- **AND** the image is retrievable under `/images/`

#### Scenario: Unsupported file
- **WHEN** a non-image file is uploaded
- **THEN** the response is 415 and nothing is stored

#### Scenario: Path components in file name
- **WHEN** the uploaded file name contains directory components
- **THEN** the file is stored under the upload folder using only its base name

### Requirement: Human Review Workflow
The system SHALL let a reviewer correct a space's `space_type` and `design_style` and advance its `review_status` strictly in the order `draft`, `in_review`, `approved`, `published`, one step per request. AI output SHALL NOT publish a space automatically.

#### Scenario: Confirm and edit
- **WHEN** a draft space is patched with `advance=true` and `design_style=Japandi`
- **THEN** its status becomes `in_review` and its style `Japandi`

#### Scenario: Invalid facet value
- **WHEN** a patch contains a `space_type` or `design_style` outside the allowed taxonomy
- **THEN** the response is 422 and the space is unchanged

#### Scenario: Past the final state
- **WHEN** a `published` space is advanced
- **THEN** the response is 409

### Requirement: Search Endpoints
The system SHALL expose the similarity and text search capabilities over HTTP and reject an unknown `space_type` filter.

#### Scenario: Unknown type
- **WHEN** text search is called with a `space_type` outside the taxonomy
- **THEN** the response is 422
