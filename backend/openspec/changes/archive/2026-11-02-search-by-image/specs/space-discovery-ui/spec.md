## ADDED Requirements

### Requirement: Photo Search On The Portfolio Page
The prototype SHALL provide a "Tìm bằng ảnh" control next to the text search on the portfolio page that lets a visitor pick one image, sends it to the photo search API, and shows the matching spaces in the same result grid as text search, together with a thumbnail of the chosen photo and a way to clear the search. A photo search and a text search SHALL replace each other's results.

#### Scenario: Successful photo search
- **WHEN** a visitor picks an interior photo
- **THEN** a thumbnail of that photo and a grid of matching spaces with the result count are shown
- **AND** each card links to that space's detail page

#### Scenario: Nothing similar
- **WHEN** the photo search returns no spaces
- **THEN** the message "Không tìm thấy công trình giống ảnh này" is shown with the thumbnail and a way to clear

#### Scenario: Rejected or failed request
- **WHEN** the photo search request fails or is rejected (wrong type, too large, too many searches)
- **THEN** an error message is announced to the visitor and the facet browser stays usable after clearing

#### Scenario: Search in progress
- **WHEN** the photo is being searched
- **THEN** the control shows a busy state and cannot start a second search until the first finishes

#### Scenario: Switching to text search
- **WHEN** a visitor submits a text query after a photo search
- **THEN** the photo thumbnail is removed and the text results replace the photo results
