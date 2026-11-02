## ADDED Requirements

### Requirement: Search By Uploaded Photo
The system SHALL accept one uploaded photo, embed it into the same vector space as the stored images without storing the photo, and return the nearest spaces in the same result shape as text search (relative path, space type, design style, score, id), ordered by descending score and optionally restricted to one `space_type`. Results SHALL exclude spaces whose score is below a fixed minimum, SHALL skip a space that is a near-identical duplicate of a higher-ranked result, and SHALL contain at most two spaces from the same project. The result size cap of text search applies.

#### Scenario: Interior photo
- **WHEN** a staff user uploads a cropped, recompressed copy of a stored living-room photo
- **THEN** the first result is the stored original or a stored near-identical duplicate of it
- **AND** results are ordered by descending score and each carries a score and the space id

#### Scenario: Not an interior photo
- **WHEN** a photo of a logo or a blank image is uploaded
- **THEN** the result is an empty list, not an error

#### Scenario: One project cannot fill the results
- **WHEN** the nearest ten spaces all belong to one project
- **THEN** at most two spaces from that project are returned and any further results come from other projects

#### Scenario: Duplicate photos in the library
- **WHEN** two stored spaces have near-identical embeddings and both rank in the results
- **THEN** only the higher-ranked one is returned

#### Scenario: Room type filter
- **WHEN** a photo is uploaded with `space_type` `phong_khach`
- **THEN** every result has `space_type` `phong_khach`

#### Scenario: Unknown room type
- **WHEN** `space_type` is not one of the known space types
- **THEN** the request is rejected with 422

#### Scenario: Photo is not kept
- **WHEN** a photo search completes
- **THEN** no file is added under the image directory and no row is added to the database

### Requirement: Photo Search Visibility
Photo search SHALL return only published spaces to visitors and spaces of every review status to staff, matching text search.

#### Scenario: Visitor
- **WHEN** a signed-out visitor searches by photo
- **THEN** every result is a published space

#### Scenario: Staff
- **WHEN** an architect searches by photo
- **THEN** draft and in-review spaces can appear in the results

### Requirement: Photo Upload Validation And Rate Limit
The photo search endpoint SHALL reject a file without a jpg, jpeg, png or webp extension or one that cannot be decoded as an image with 415, SHALL reject a file larger than a fixed size limit with 413, and SHALL answer at most a fixed number of requests per client per minute, then 429 with `Retry-After`. No upload SHALL produce a 500.

#### Scenario: Wrong file type
- **WHEN** a `.pdf` file is uploaded
- **THEN** the response is 415

#### Scenario: Corrupt image
- **WHEN** a file named `photo.jpg` whose bytes are not an image is uploaded
- **THEN** the response is 415

#### Scenario: Oversized upload
- **WHEN** a photo larger than the size limit is uploaded
- **THEN** the response is 413

#### Scenario: Too many searches
- **WHEN** one client sends more photo searches in a minute than the limit
- **THEN** the extra requests get 429 with a `Retry-After` header
