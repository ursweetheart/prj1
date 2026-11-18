# image-sizes Specification

## Purpose
TBD - created by archiving change publishing-workflow. Update Purpose after archive.

## Requirements

### Requirement: Optimised copies at several widths
Each stored photo SHALL have WebP copies 480, 960 and 1600 pixels wide, never wider than the original, and its original pixel width and height SHALL be stored (act-1 "tối ưu dung lượng, tạo các kích thước"; class-6 Anh). The copies SHALL be made when the photo is processed, and a backfill SHALL make them for existing photos. The API SHALL return the available widths with each photo. The original file SHALL stay untouched.

#### Scenario: New upload
- **WHEN** a 4000×3000 photo is processed
- **THEN** copies 480, 960 and 1600 px wide exist, and the photo reports 4000×3000

#### Scenario: Small original
- **WHEN** a photo is 800 px wide
- **THEN** only the 480 px copy is made, and pages use the original above that

### Requirement: Pages load a fitting size
Photo cards and the review list SHALL offer the copies with `srcset` and `sizes`, so a phone loads a small copy. A photo without copies SHALL fall back to the original.

#### Scenario: Phone
- **WHEN** the space explorer is opened at 360 px
- **THEN** the cards load the 480 px copies, not the originals
