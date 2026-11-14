## Purpose

Lets the lead architect see and edit the taxonomy (dimensions, values, synonyms, order and visibility) from the site instead of Swagger (seq-15, NFR-13), with the effect of each change shown before it is made and every change logged.

## ADDED Requirements

### Requirement: Who may manage the taxonomy
Viewing the admin tree and every change to dimensions and values SHALL be limited to the lead architect and admin roles. Other signed-in users SHALL get 403 and anonymous requests 401. The public taxonomy list used by the filters SHALL stay public.

#### Scenario: Sales opens the tree
- **WHEN** a sales user requests the admin tree
- **THEN** the server answers 403

#### Scenario: Visitor filters still work
- **WHEN** an anonymous visitor opens `/khong-gian`
- **THEN** the filters load from the public taxonomy list as before

### Requirement: Taxonomy tree with usage
The "Danh mục" tab on `/quan-tri/phan-loai` SHALL list every dimension in filter order with its name, code, whether it is shown to visitors, and its values. Each value SHALL show its name, code, synonyms, and the number of spaces and of published spaces tagged with it. The existing review of AI proposals SHALL stay available on a second tab, "Đề xuất của AI".

#### Scenario: Open the tree
- **WHEN** a lead architect opens `/quan-tri/phan-loai`
- **THEN** "Danh mục" is shown first, with "Phong cách" listing values such as "Japandi · 6 không gian, 6 đã đăng"

### Requirement: Add a value
An approver SHALL be able to add a value to a dimension with a name, an optional description and synonyms. The code SHALL be derived from the name (lower case, without accents, words joined by `_`) and shown before saving. A name whose code already exists in that dimension SHALL be refused. The value SHALL be usable for tagging and filtering right away.

#### Scenario: New style
- **WHEN** the lead architect adds "Địa Trung Hải" to "Phong cách"
- **THEN** the code shown is `dia_trung_hai`, the value appears in the tree with 0 spaces, and the public taxonomy list includes it

#### Scenario: Duplicate
- **WHEN** they add "Japandi" to "Phong cách" again
- **THEN** the server answers 409 and the form says the value already exists

### Requirement: Edit a value
An approver SHALL be able to rename a value, and edit its description and synonyms. Renaming SHALL keep the code, so tags and filter links keep working. Synonyms SHALL be stored trimmed, in lower case and without duplicates. They SHALL be used right away, both by the assistant's request parsing (which compares them without accents) and by the material tagging (which compares them with accents).

#### Scenario: Add a customer word
- **WHEN** the lead architect adds the synonyms "  Bắc Âu , bắc âu" to "Scandinavian" in "Phong cách"
- **THEN** they are stored as "bắc âu" once, and the chat message "phòng khách kiểu bac au" is understood as the style Scandinavian

#### Scenario: Rename
- **WHEN** they rename "Hiện đại" to "Hiện đại tối giản"
- **THEN** the code stays `Hien_dai` and `/khong-gian#phong_cach=Hien_dai` still filters the same spaces

### Requirement: Merge with a warning
Before merging, the screen SHALL show how many spaces and how many projects carry the source value and ask for confirmation. Only another value of the same dimension SHALL be offered as the target.

#### Scenario: Confirm a merge
- **WHEN** the lead architect chooses to merge "Tối giản" into "Hiện đại"
- **THEN** the screen states how many spaces and projects will move, and nothing changes until they confirm

### Requirement: Add and edit dimensions
An approver SHALL be able to add a dimension by hand with a name, whether a space may carry several of its values, and whether it is shown to visitors. They SHALL be able to rename a dimension, show or hide it for visitors, and move it up or down in the filter order. The code SHALL be derived from the name and SHALL NOT change afterwards.

#### Scenario: Hide a dimension
- **WHEN** the lead architect hides "Mức đầu tư"
- **THEN** the filters on `/khong-gian` no longer offer "Mức đầu tư", and its tags are kept

#### Scenario: Reorder
- **WHEN** they move "Vật liệu" up one place
- **THEN** it swaps order with the dimension above it, and the filters show the new order

#### Scenario: Manual dimension
- **WHEN** they add the dimension "Ánh sáng" with several values allowed and shown to visitors
- **THEN** it appears at the end of the tree with code `anh_sang` and no values, ready for values to be added

### Requirement: Change log
Every add, rename, edit, merge, show/hide and reorder SHALL be recorded with the user, the time, what changed and the values before and after. The tree SHALL show the 20 most recent changes.

#### Scenario: Log after a rename
- **WHEN** the lead architect renames a value
- **THEN** "Gần đây" lists that rename with their email, the time and the old and new names

### Requirement: Usable on a phone and by keyboard
The admin tab SHALL be usable at 360px without sideways page scroll, and every action SHALL be reachable and confirmable by keyboard. Forms SHALL show their errors next to the field.

#### Scenario: Phone
- **WHEN** a lead architect opens the tab on a 360px screen
- **THEN** every dimension and value is readable and the page does not scroll sideways
