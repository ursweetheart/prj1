## MODIFIED Requirements

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
