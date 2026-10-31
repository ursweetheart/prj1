# space-vector-store Specification

## Purpose
Created by archiving change ai-space-search-and-review.

## Requirements
### Requirement: Persistent Space Records With Embeddings
The system SHALL store one record per image (`Space`) in Postgres with its facets, caption, alt text, color palette, furniture hotspots, review status and image embedding, keyed uniquely by the image path relative to the image root.

#### Scenario: Store a classified image
- **WHEN** a processed image is saved
- **THEN** a `space` row exists with `space_type`, `design_style`, `style_confidence`, `materials`, `caption`, `alt_text`, `palette`, `hotspots` and a non-null `embedding`
- **AND** the row's `review_status` is `draft` if it did not exist before

#### Scenario: Re-ingest an existing image
- **WHEN** an image whose `relative_path` already exists is processed again
- **THEN** its classification fields and embedding are updated in place without creating a duplicate
- **AND** its `review_status` is left unchanged

### Requirement: Reproducible Database Setup
The system SHALL provide `schema.sql` and a Docker Compose service so a fresh environment creates the pgvector extension and the `space` table automatically.

#### Scenario: Fresh environment
- **WHEN** `docker compose up -d` runs against an empty data volume
- **THEN** the `vector` extension and the `space` table with an `embedding vector(768)` column exist

### Requirement: Re-embedding Without Re-classification
The system SHALL recompute every stored embedding with the current embedder without calling the classification model.

#### Scenario: Embedder changed
- **WHEN** `reembed.py` runs
- **THEN** the embedding column is resized to the embedder's dimension and refilled for all rows
- **AND** no facet, caption or review status value changes
