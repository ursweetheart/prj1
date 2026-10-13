## MODIFIED Requirements

### Requirement: Multimodal Vision Embedding Generation
The system SHALL generate high-dimensional semantic feature vectors from images using OpenCLIP SigLIP2 ViT-B/16 for downstream similarity search (`M3`) and vector indexing (`M10`), and SHALL persist the vector with the space record.

#### Scenario: Generate normalized vector embedding
- **WHEN** an interior image is loaded into the SigLIP2 model
- **THEN** the system outputs a 768-dimensional normalized float32 vector embedding
- **AND** the embedding is stored in the vector index together with the space record

#### Scenario: Text query in the same space
- **WHEN** a Vietnamese text description is embedded with the same model
- **THEN** the resulting 768-dimensional normalized vector is directly comparable to image vectors by cosine similarity
