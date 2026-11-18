# taxonomy/data-driven-taxonomy Specification

## Purpose
Move the taxonomy out of code (the `Literal` enums in `pipeline/schemas.py` and the synonym dicts in `pipeline/assistant.py`) into database-backed dimensions, values, synonyms, and staged candidates, with stable identifiers so edits never break facet URLs. This enables UC15 and NFR-13 and is the prerequisite for automatic discovery.

## Requirements

### Requirement: Data-Driven Dimensions and Values
The taxonomy SHALL store dimensions (`ChieuPhanLoai`) and values (`GiaTriPhanLoai`) as data, each with an immutable `ma_dinh_danh` distinct from its editable display name, and classification and search SHALL read the allowed values from this data rather than from hardcoded enums.

#### Scenario: Adding a value without code changes
- **WHEN** a lead architect adds a new value to an existing dimension through the taxonomy admin
- **THEN** the value becomes available for tagging and filtering immediately, with no code deployment (NFR-13).

#### Scenario: Renaming keeps identity
- **WHEN** a lead architect renames a value's display name
- **THEN** the `ma_dinh_danh` is unchanged, existing tags and facet URLs keep resolving, and only the displayed label changes.

### Requirement: Synonyms Drive Request Parsing
Each value SHALL carry a `tu_dong_nghia` list, and the assistant's request parsing SHALL resolve customer vocabulary to values via this data, seeded from the former hardcoded dicts.

#### Scenario: Synonym resolves to a value
- **WHEN** a customer message contains a term listed in a value's `tu_dong_nghia`
- **THEN** request parsing maps the message to that value's `ma_dinh_danh` without any code change to add the term.

### Requirement: Value Merge Migrates Labels
Merging two values SHALL move every tag from the source value to the target value, delete the source, and enqueue a re-index task, warning first how many projects are affected. Both values SHALL belong to the same dimension, a mirrored space column (design style, space type) SHALL move with the tags, and values the system computes (`tong_mau`) SHALL NOT be merged.

#### Scenario: Merging two values
- **WHEN** a lead architect merges value A into value B
- **THEN** the system shows the affected project count, and on confirmation re-points all A tags to B, removes A, and queues the vector-index refresh (seq-15 b16–22).

#### Scenario: Merging a style moves the space column
- **WHEN** "Toi_gian" is merged into "Hien_dai" in `phong_cach`
- **THEN** every space whose design style was `Toi_gian` now has `Hien_dai`, carries the `phong_cach:Hien_dai` tag, and keeps it after its caption is edited

#### Scenario: Different dimensions
- **WHEN** a merge names a source in `vat_lieu` and a target in `phong_cach`
- **THEN** the server answers 422 and nothing changes

#### Scenario: Computed dimension
- **WHEN** a merge names two `tong_mau` values
- **THEN** the server answers 422, because those values come from the colour extractor

### Requirement: Candidate Staging Entity
AI-proposed taxonomy changes SHALL be stored as `UngVienPhanLoai` rows marked unreviewed, and SHALL never become live dimensions or values until a human accepts them.

#### Scenario: Proposal awaits review
- **WHEN** the discovery pipeline promotes a candidate dimension
- **THEN** it is written as an `UngVienPhanLoai` row marked `[AI SINH - CHƯA DUYỆT]` and does not appear as a usable facet to customers.

### Requirement: Automatic Tagging Uses Stored Values
When a photo is tagged automatically, the room type and the style SHALL be chosen only from the values currently stored for the `khong_gian` and `phong_cach` dimensions. The AI SHALL be given each value's display name and description, and its answer SHALL be matched to a value by identifier, display name, or synonym, ignoring case and accents.

#### Scenario: A value added by staff is used on the next upload
- **WHEN** a lead architect adds the value "Mid-century" with a description to `phong_cach`, and a photo is then uploaded that the AI judges to be Mid-century
- **THEN** the photo is saved with that value's identifier as its style and carries its `phong_cach` tag, with no code change or redeploy

#### Scenario: Answer given as a display name or synonym
- **WHEN** the AI answers "Hiện đại", "hien dai" or another phrase listed in the synonyms of `Hien_dai`
- **THEN** the photo's style is saved as `Hien_dai`

#### Scenario: Description guides the AI
- **WHEN** a lead architect edits the description of a style value
- **THEN** the next automatic tagging run gives the AI the edited description for that value

#### Scenario: Merged value is no longer offered
- **WHEN** value A has been merged into value B and a photo is then tagged automatically
- **THEN** A is not offered to the AI and is never saved as the photo's style or room type

#### Scenario: Database unreachable
- **WHEN** automatic tagging runs while the taxonomy tables cannot be read
- **THEN** the values from the seed file are used, and tagging still completes

### Requirement: Staff Edits and Search Accept Stored Values
Editing a photo's room type or style, and filtering search by room type, SHALL accept exactly the values currently stored for `khong_gian` and `phong_cach`, and SHALL reject anything else with 422.

#### Scenario: Staff set a newly added style
- **WHEN** a staff member edits a photo's style to a value added to `phong_cach` at `/quan-tri/phan-loai`
- **THEN** the edit is saved and the photo carries that value's tag

#### Scenario: Unknown value rejected
- **WHEN** a request sets `design_style` or filters `space_type` with a code that is not stored
- **THEN** the server answers 422 listing the allowed codes, and nothing changes

### Requirement: Unmatched Answers Fall Back to Other
If an automatic tagging answer for room type or style matches no stored value, the system SHALL save the dimension's "Other" value (`khac` for `khong_gian`, `Khac` for `phong_cach`) and SHALL NOT substitute any other value. An unmatched style SHALL be saved with confidence 0 so it is flagged for staff review.

#### Scenario: Unknown style
- **WHEN** the AI answers a style "Art deco" that is not a stored value or synonym
- **THEN** the photo's style is `Khac` with confidence 0, and it is listed among the photos where the AI was not sure

#### Scenario: Unknown room type
- **WHEN** the AI answers a room type that is not a stored value or synonym
- **THEN** the photo's room type is `khac`, not `phong_khach`

#### Scenario: Offline fallback names a removed value
- **WHEN** tagging runs without the AI and the folder-name rules pick a style whose value has been merged away
- **THEN** the photo's style is `Khac` with confidence 0
