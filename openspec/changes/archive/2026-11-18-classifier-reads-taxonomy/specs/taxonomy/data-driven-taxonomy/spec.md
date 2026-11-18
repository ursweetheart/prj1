## ADDED Requirements

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
