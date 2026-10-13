## ADDED Requirements

### Requirement: Taxonomy-Compliant Multi-Facet Classification
The system SHALL classify each interior image at the `Space` level into multi-dimensional facets adhering to the D3 Studio design taxonomy.

#### Scenario: Classify space type and primary style
- **WHEN** an interior image and its pre-extracted feature metadata (color palette, detected objects) are supplied to the multimodal reasoning model
- **THEN** the system outputs a validated JSON structure identifying:
  - `space_type` (e.g., `living_room`, `master_bedroom`, `kitchen`, `dining_room`, `entryway`, `lounge`)
  - `design_style` (e.g., `Indochine`, `Japandi`, `Wabi-sabi`, `Modern`, `Neoclassic`, `Luxury`, `Minimalist`)
  - `materials` (e.g., `walnut_wood`, `cane_webbing`, `linen`, `marble`, `smoked_glass`)
  - `confidence_score` for each classification.

### Requirement: Grounded LLM Prompting via Quantitative Features
The system SHALL synthesize pre-extracted color palettes and detected object labels directly into the prompt context to prevent LLM hallucinations.

#### Scenario: Grounded style reasoning
- **WHEN** detected objects include `cane webbing bed`, `lotus artwork`, `dark wood wardrobe` and the palette contains deep earthy browns
- **THEN** the model cites these specific visual cues in its rationale field when predicting `Indochine` style.

### Requirement: Automated SEO Alt-Text and Space Caption Generation
The system SHALL generate concise, professional Vietnamese alt-text and captions optimized for search engines (`NFR-07`).

#### Scenario: Generate accessible and SEO-friendly metadata
- **WHEN** classification finishes successfully
- **THEN** the output contains a Vietnamese caption (15–30 words) summarizing the space's design characteristics
- **AND** generates an image `alt_text` combining space type, style, key material, and D3 Studio brand attribution.

### Requirement: Human-in-the-Loop Review Verification
The system SHALL surface AI predictions as proposed suggestions (Draft state) for architect verification, upholding NFR-10 ($\ge 85\%$ accuracy).

#### Scenario: Architect confirmation in CMS
- **WHEN** an architect views the newly ingested image in the CMS publishing queue
- **THEN** all suggested facet tags are pre-selected for single-click approval or modification
- **AND** upon approval, the record transitions from `Draft` to `In Review` / `Approved`.
