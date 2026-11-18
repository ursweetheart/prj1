## ADDED Requirements

### Requirement: Sorting the explorer
The space explorer's filtered results SHALL be sortable by newest first (publish date), most viewed in the last 30 days, or style name (BFD 1.2), from a control in the filter panel. Newest SHALL be the default, and the choice SHALL be kept in the page's URL.

#### Scenario: Most viewed
- **WHEN** a visitor picks "Xem nhiều nhất"
- **THEN** the most viewed published photos of the last 30 days come first

### Requirement: Search note
After a description or photo search, `/khong-gian` SHALL show above the results, as a live region:
- the constraints taken from the description;
- the photo's traits, or the non-interior refusal;
- the rewording hint, when the matches are weak.

Clearing the search SHALL remove the note.

#### Scenario: Photo search note
- **WHEN** a visitor searches with a warm Wabi-sabi living-room photo
- **THEN** "Ảnh của bạn có vẻ thuộc phong cách Wabi-sabi, tông màu Ấm" is shown above the results
