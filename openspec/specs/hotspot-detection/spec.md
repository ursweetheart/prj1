# hotspot-detection Specification

## Purpose

Propose a small set of well-placed hotspots for each uploaded photo, on the furniture and fittings an interior studio wants to show, so staff only need to adjust them rather than clean them up.

## Requirements

### Requirement: Items Named and Pointed by the Classifier
When a photo is classified at upload, the same AI call SHALL also return up to 8 main interior items, each with a Vietnamese name, a category from a fixed list, and a box around the item in photo coordinates; the item's point is the centre of that box. Identical items (for example matching dining chairs) SHALL be listed once. No additional AI call SHALL be made for hotspots.

#### Scenario: Items the detector cannot see
- **WHEN** a living-room photo with a chandelier, a rug and a sofa is uploaded
- **THEN** its hotspots include points named for the chandelier and the rug, each lying on that item

#### Scenario: Point on the item, not in empty space
- **WHEN** an L-shaped sofa is detected and the AI also points at it
- **THEN** the hotspot uses the centre of the AI's box around the sofa, not the centre of the detection box

### Requirement: Merging Detector and AI Items
An AI item whose point lies inside a detector box SHALL be merged with it into one hotspot that keeps the AI's name and point and the detector's box, confidence and label. An AI item matching no box SHALL become a hotspot without a box. A detector box matching no AI item SHALL be kept only when it is a furniture class with confidence of at least 0.5. Every proposed hotspot SHALL record its origin as AI.

#### Scenario: Matched
- **WHEN** the AI points inside a detector box labelled "couch" and names it "Sofa vải xám"
- **THEN** there is one hotspot named "Sofa vải xám", at the AI's point, with the couch box and confidence

#### Scenario: Unmatched weak detection
- **WHEN** the detector finds a chair at confidence 0.45 that the AI did not name
- **THEN** no hotspot is proposed for it

### Requirement: Clean Proposals
Proposed hotspots SHALL exclude small objects (bottle, cup, bowl, book, glass, cutlery, remote, phone, person and similar), detections below 0.4 confidence, and duplicates (same label with boxes overlapping by more than half of the smaller box), and SHALL number at most 6 per photo. They SHALL be chosen in this order: merged items, then AI-only items, then detector-only items, larger items first within each group.

#### Scenario: Clutter and duplicates removed
- **WHEN** the detector finds two overlapping "couch" boxes, a bottle and three cups
- **THEN** the photo gets one sofa hotspot and none for the bottle or cups

#### Scenario: Cap
- **WHEN** ten valid items are found in a photo
- **THEN** six hotspots are proposed, merged ones first

#### Scenario: AI unavailable
- **WHEN** a photo is uploaded while the AI cannot be reached
- **THEN** its hotspots come from the detector alone, cleaned and capped the same way

### Requirement: One Hotspot per Distinct Item
A photo SHALL get one hotspot per distinct item: AI items with the same name (ignoring case and spacing) count once, and a detector-only box SHALL be dropped when the AI already named an item of its class. Without AI items, the detector keeps one hotspot per class.

#### Scenario: Matching chairs
- **WHEN** a dining table has six identical chairs and an orange armchair stands nearby
- **THEN** there is one hotspot for the dining chairs and one for the armchair

### Requirement: Re-run for Untouched Drafts
A one-off command SHALL rebuild the proposed hotspots of draft photos whose hotspots no person has touched: no hand-made point, no point linked to an item, and no hotspot edit in the review log. Other photos SHALL NOT change. Each rebuilt photo SHALL have its previous hotspots written to its review log, and a dry run SHALL report how many photos would change without changing them.

#### Scenario: Hand-edited draft is skipped
- **WHEN** a draft has a point a reviewer dragged or linked to an item
- **THEN** the re-run leaves all of that photo's hotspots unchanged

#### Scenario: Published photo is skipped
- **WHEN** the re-run reaches a published photo
- **THEN** its hotspots are unchanged

#### Scenario: Previous hotspots kept on record
- **WHEN** the re-run rebuilds a draft's hotspots
- **THEN** the review log holds the previous hotspots, and the photo now has at most 6

#### Scenario: Restore, then rebuild again
- **WHEN** staff restore the previous hotspots of rebuilt drafts nobody has edited since
- **THEN** those drafts get their previous hotspots back and count as untouched for a later re-run
