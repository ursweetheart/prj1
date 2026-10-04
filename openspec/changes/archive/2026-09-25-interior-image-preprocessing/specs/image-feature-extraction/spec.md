## ADDED Requirements

### Requirement: Color Palette and Tone Extraction
The system SHALL extract the dominant color palette and categorize lighting tone from interior images using K-Means clustering in the CIE-Lab color space.

#### Scenario: Successful palette and tone extraction
- **WHEN** an interior image from `image_d3/` is processed by the color extraction module
- **THEN** the system returns a palette of 5 distinct hex color codes with their corresponding pixel occupancy percentages
- **AND** determines brightness category (`light`, `dark`, or `balanced`) and color temperature (`warm`, `cool`, or `neutral`)
- **AND** execution completes without allocating GPU VRAM (CPU-bound operation).

### Requirement: Furniture Object Detection for Hotspots
The system SHALL detect interior furniture objects and output localized bounding box coordinates compatible with the CMS Hotspot feature (`M7`).

#### Scenario: Detect common furniture items
- **WHEN** an interior image is passed through the lightweight `YOLO-World-S` model
- **THEN** the system outputs a list of detected furniture items (such as `sofa`, `coffee table`, `bed`, `pendant light`, `dining table`, `wardrobe`)
- **AND** provides bounding box normalized coordinates `[x_min, y_min, x_max, y_max]` and confidence scores $\ge 0.35$.

### Requirement: Multimodal Vision Embedding Generation
The system SHALL generate high-dimensional semantic feature vectors from images using OpenCLIP ViT-B/32 for downstream similarity search (`M3`) and vector indexing (`M10`).

#### Scenario: Generate normalized vector embedding
- **WHEN** an interior image is loaded into the OpenCLIP model
- **THEN** the system outputs a 512-dimensional normalized float32 vector embedding
- **AND** the embedding is formatted ready for insertion into the vector index.

### Requirement: Strict VRAM Boundary on 4GB GPUs
The system SHALL enforce sequential pipeline execution and memory cleanup to maintain total VRAM usage below 2.5GB on 4GB GPUs (RTX 3050).

#### Scenario: Consecutive batch inference without memory leak
- **WHEN** 50 interior images are processed consecutively in batch or stream mode
- **THEN** peak GPU VRAM allocation remains under 2.5GB at all times
- **AND** `torch.cuda.empty_cache()` or explicit garbage collection is triggered between stages to prevent CUDA Out Of Memory (OOM) errors.
