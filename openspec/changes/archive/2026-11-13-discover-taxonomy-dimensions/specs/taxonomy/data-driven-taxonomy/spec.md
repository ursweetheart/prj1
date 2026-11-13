## Purpose

Move the taxonomy out of code (the `Literal` enums in `pipeline/schemas.py` and the synonym dicts in `pipeline/assistant.py`) into database-backed dimensions, values, synonyms, and staged candidates, with stable identifiers so edits never break facet URLs. This enables UC15 and NFR-13 and is the prerequisite for automatic discovery.

## ADDED Requirements

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
Merging two values SHALL move every tag from the source value to the target value, delete the source, and enqueue a re-index task, warning first how many projects are affected.

#### Scenario: Merging two values
- **WHEN** a lead architect merges value A into value B
- **THEN** the system shows the affected project count, and on confirmation re-points all A tags to B, removes A, and queues the vector-index refresh (seq-15 b16–22).

### Requirement: Candidate Staging Entity
AI-proposed taxonomy changes SHALL be stored as `UngVienPhanLoai` rows marked unreviewed, and SHALL never become live dimensions or values until a human accepts them.

#### Scenario: Proposal awaits review
- **WHEN** the discovery pipeline promotes a candidate dimension
- **THEN** it is written as an `UngVienPhanLoai` row marked `[AI SINH - CHƯA DUYỆT]` and does not appear as a usable facet to customers.
