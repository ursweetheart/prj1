# space-discovery-ui Specification

## Purpose
Created by archiving change ai-space-search-and-review.
## Requirements
### Requirement: Text Search On The Portfolio Page
The prototype SHALL provide a search box on the portfolio page that sends the typed description to the search API and shows the matching spaces as cards in place of the facet browser, with a way to clear the search.

#### Scenario: Successful search
- **WHEN** a visitor submits "phòng ngủ ấm áp tông gỗ"
- **THEN** a grid of matching spaces is shown with the result count and the query
- **AND** each card links to that space's detail page

#### Scenario: API unavailable
- **WHEN** the search request fails
- **THEN** an error message is announced to the visitor and the facet browser stays usable after clearing

#### Scenario: Empty query
- **WHEN** the search box is submitted empty
- **THEN** the search state is cleared and the facet browser is shown

### Requirement: Space Detail Page With Similar Spaces
The prototype SHALL provide a detail page per space showing the image, space type and style, caption, materials and color palette, followed by a "Dự án tương tự" block of similar spaces from the API.

#### Scenario: Open a space
- **WHEN** a visitor opens `/khong-gian/<id>`
- **THEN** the image, caption and palette of that space are shown
- **AND** up to eight similar spaces of the same type are listed, each linking to its own detail page

#### Scenario: Navigate between similar spaces
- **WHEN** a visitor opens a similar space from the block
- **THEN** the page reloads its content for the new id and scrolls to the top

#### Scenario: Unknown space
- **WHEN** the id does not exist
- **THEN** a "not found" message is shown instead of the page content

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

