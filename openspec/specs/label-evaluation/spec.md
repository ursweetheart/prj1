# label-evaluation Specification

## Purpose
TBD - created by archiving change labelling-queue-feedback. Update Purpose after archive.

## Requirements

### Requirement: The AI's proposal is kept with its confidence
For every processed photo, the system SHALL keep the room type and style the AI proposed, each with a confidence between 0 and 1 (seq-1 step 11). A person's later changes SHALL NOT alter this record. Re-running the AI on a draft SHALL replace it.

#### Scenario: Reviewer changes the style
- **WHEN** the AI proposed Luxury at 0.62 and a reviewer saves Japandi
- **THEN** the photo's style is Japandi, and its AI proposal is still Luxury at 0.62

### Requirement: Confidence shown to the reviewer
The review page SHALL show, beside the room type and style of each photo, the AI's proposal and its confidence in percent (seq-1 step 17), for example "AI: Luxury · 62%". A confidence under 70% SHALL be marked "AI chưa chắc". The marking SHALL use text, not colour alone.

#### Scenario: Low confidence
- **WHEN** a draft's style was proposed at 0.55
- **THEN** its card shows "AI: <style> · 55%" with "AI chưa chắc"

### Requirement: Corrected labels are recorded for model evaluation
When a reviewer saves a room type or style that differs from the AI's proposal, the system SHALL record a correction (seq-1 step 21): the photo, the dimension, the AI's value and confidence, the correct value, who and when. There SHALL be one record per photo and dimension, holding the latest correct value. Saving the AI's value again SHALL remove the record. An approver's accept or map of a suggested value SHALL update the corrections of the photos it moves.

#### Scenario: Correction then revert
- **WHEN** a reviewer changes a photo's style from the AI's Luxury to Japandi, and later back to Luxury
- **THEN** first one correction "Luxury → Japandi" exists, and after the revert none does

#### Scenario: Suggested value accepted
- **WHEN** a photo's style went from the AI's Indochine to "Khác" while waiting for "Farmhouse", and the approver accepts Farmhouse
- **THEN** its correction reads "Indochine → farmhouse"

### Requirement: Accuracy measured from the corrections
The evaluation tool SHALL report, over photos a person has moved out of draft:
- for room type and style, the share where the AI's proposal equals the final label, against the 85% target (NFR-10);
- the same accuracy per confidence band (under 0.5, 0.5–0.7, 0.7–0.9, 0.9 and above);
- the list of corrections.

With fewer than 30 reviewed photos it SHALL say the number is not yet reliable.

#### Scenario: Report
- **WHEN** 40 photos have been reviewed and 6 styles were corrected
- **THEN** the tool reports style accuracy 34/40 = 85% "meets the target", the per-band accuracy, and the 6 corrections
