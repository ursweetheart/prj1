## Purpose

Produce dimension candidates independently from three sources — images, conversations, and behavior — by calling Gemini to analyze each source (no training), and represent every candidate uniformly as a scored proposal so sources are comparable. A candidate dimension is a new classification axis, orthogonal to the current taxonomy.

## ADDED Requirements

### Requirement: Image-Derived Candidate Proposals
The image emitter SHALL send a capped sample of existing per-space material (captions / transcripts and/or sample images) together with the current taxonomy to Gemini, and collect proposed dimensions that are absent from the current taxonomy, each with candidate values, example space ids, and a confidence.

#### Scenario: Capture artifacts are not dimensions
- **WHEN** Gemini is asked to propose dimensions from the library
- **THEN** it is instructed to ignore photographic / capture properties (angle, lighting, which scrape or photographer), so "render style" is not proposed as a design dimension.

#### Scenario: Orthogonality is required
- **WHEN** a proposed dimension only separates spaces within a single existing facet value
- **THEN** it is treated as a value/synonym signal, not a dimension candidate, and is down-scored.

### Requirement: Conversation Knowledge-Gap Signals
When an assistant answer falls below the retrieval thresholds, `respond()` SHALL log the question and the folded customer terms that mapped to no existing value, instead of discarding them, and recurring gaps SHALL be fed to the proposer as a source that can raise or contribute candidates.

#### Scenario: Unanswered topic is captured
- **WHEN** a customer question scores below `MIN_SCORE` / `MIN_TEXT_SCORE`
- **THEN** a knowledge-gap record (question + unmapped terms + best cosine) is stored in addition to any handoff lead (act-4 b8).

### Requirement: Consented Behavior Signals
Behavior events (`SuKien` / `PhienTruyCap`) SHALL be collected only for sessions with recorded consent, enriched with the viewed content's facet values, and their facet co-occurrence SHALL feed the demand component of a candidate's score.

#### Scenario: No consent, no event
- **WHEN** a visitor has not consented to data collection
- **THEN** no per-session event is persisted and only anonymous aggregates are kept (act-3 b8, NFR-09).

### Requirement: Scored Candidate Representation
Every candidate from every source SHALL be represented uniformly as a proposal record — dimension name, candidate values, example space ids, per-source evidence, and a score — so candidates from different sources can be compared and merged by score.

#### Scenario: Comparable candidates
- **WHEN** an image proposal and a conversation signal describe the same new dimension
- **THEN** they are merged into one proposal record whose evidence lists both sources.
