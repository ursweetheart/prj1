## ADDED Requirements

### Requirement: Similar Spaces By Image
The system SHALL return the spaces most similar to a given space, ranked by cosine similarity, excluding the query space itself and returning only spaces of the same `space_type`.

#### Scenario: Similar bedrooms
- **WHEN** similar spaces are requested for a `phong_ngu_master` space
- **THEN** every result has `space_type` `phong_ngu_master` and none is the query space
- **AND** each result carries a similarity score and the space id

#### Scenario: Unknown space
- **WHEN** similar spaces are requested for a path that is not stored
- **THEN** the result is empty

### Requirement: Search By Natural-Language Text
The system SHALL embed a free-text query, including Vietnamese, into the same vector space as the images and return the nearest spaces, optionally restricted to one `space_type`.

#### Scenario: Vietnamese query with type filter
- **WHEN** the query "phòng ngủ ấm áp tông gỗ" is searched with `space_type` `phong_ngu_master`
- **THEN** all results are `phong_ngu_master` spaces ordered by descending score

#### Scenario: Style named in the query
- **WHEN** the query "phòng ngủ phong cách Indochine giường mây" is searched
- **THEN** most top results are Indochine bedrooms

### Requirement: Bounded Result Size
The system SHALL cap the number of returned results at a fixed maximum regardless of the requested size.

#### Scenario: Oversized request
- **WHEN** a client asks for more than the maximum number of results
- **THEN** at most the maximum is returned
