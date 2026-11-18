## ADDED Requirements

### Requirement: Photo interactions
For a consenting visitor the system SHALL record:
- `phong_to_anh` when a project photo is opened full screen by the visitor, naming the project slug and photo number;
- `chuyen_anh` when the visitor steps to another photo in that view, naming the new photo;
- `bam_hotspot` when a hotspot card is opened on a space page, naming the photo and the item (or the hotspot's label).

Opening a photo from a shared link SHALL NOT count as `phong_to_anh`. The usual consent and staff rules SHALL apply.

#### Scenario: Zoom and step
- **WHEN** a consenting visitor clicks photo 3 of `beaumont-lounge` and presses the right arrow
- **THEN** a `phong_to_anh` event with object `beaumont-lounge/3` and a `chuyen_anh` event with object `beaumont-lounge/4` are stored

#### Scenario: Hotspot opened without consent
- **WHEN** a visitor who declined opens the "Sofa" card
- **THEN** no event row is stored, and the day's `bam_hotspot` count increases by one

### Requirement: Photo interactions on the trend dashboard
The behaviour section of the trend dashboard SHALL show the consented and anonymous counts of the three photo events and the ten most opened hotspots.

#### Scenario: Reading the block
- **WHEN** sales opens the behaviour section after visitors opened the sofa card of photo 12 four times
- **THEN** "Tương tác với ảnh" lists the zoom, step and hotspot counts, and the hotspot list shows photo 12's sofa with 4
