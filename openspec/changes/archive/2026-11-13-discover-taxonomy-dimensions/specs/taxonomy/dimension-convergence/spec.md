## Purpose

Decide which candidate dimensions are worth proposing by scoring them on evidence that combines across independent sources, filter out non-distinct or un-nameable proposals, and route survivors to a human for approval and library rollout.

## ADDED Requirements

### Requirement: Evidence Score and Multi-Source Agreement
Each candidate dimension SHALL carry an evidence score combining coverage, distinctness, and demand; independent support from a second source SHALL raise the score, and only candidates above a calibrated threshold SHALL be promoted. A single-source candidate below threshold SHALL be kept as pending, not promoted.

#### Scenario: Two sources raise a candidate
- **WHEN** an image proposal and a behavior demand signal describe the same new dimension
- **THEN** the merged candidate's score reflects both sources and crosses the promotion threshold.

#### Scenario: Lone low-score candidate is held
- **WHEN** a candidate is supported by only one source and scores below threshold
- **THEN** it is kept as "pending more evidence" and is not proposed to a human.

### Requirement: Distinctness and Nameability Check
A promoted candidate SHALL pass a Gemini check confirming it is not already expressible via the existing taxonomy and that each value is nameable with a short Vietnamese phrase; proposals that fail SHALL be down-scored and not promoted.

#### Scenario: Non-distinct proposal rejected
- **WHEN** a proposed dimension merely rephrases an existing dimension or value
- **THEN** the distinctness check fails and the candidate is not proposed.

### Requirement: Human Approval Before Any Dimension Exists
The pipeline SHALL never create a live dimension automatically; a new `ChieuPhanLoai` SHALL be created only after a human accepts the corresponding `UngVienPhanLoai`.

#### Scenario: Review with score breakdown
- **WHEN** a lead architect opens a promoted candidate
- **THEN** they see the proposed name, value labels, example images, and the score breakdown (coverage / distinctness / demand, and which sources contributed) before accepting or rejecting.

### Requirement: Rollout on Acceptance
Accepting a candidate SHALL create the dimension, back-tag the existing library by having Gemini tag each space along the new dimension, and generate the new filter and SEO URLs, flagging low-confidence tags for review.

#### Scenario: Library back-tagged
- **WHEN** a lead architect accepts a candidate dimension
- **THEN** the dimension is created, every existing space receives a value along it (low-confidence ones flagged per QT01 "đủ features bắt buộc"), and the new facet filter and its SEO URLs become available.
