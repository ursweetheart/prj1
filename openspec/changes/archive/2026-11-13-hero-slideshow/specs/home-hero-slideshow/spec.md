## ADDED Requirements

### Requirement: Hero images come from a folder
The home hero SHALL show every image file (jpg, jpeg, png, webp, avif) in `src/assets/hero/`, ordered by file name, without any other code change.

#### Scenario: Adding a photo
- **WHEN** an editor puts `02-villa.jpg` into `src/assets/hero/` next to `01-indochine-apartment.jpg`
- **THEN** the hero shows `01-indochine-apartment.jpg` first and `02-villa.jpg` second

#### Scenario: Single photo
- **WHEN** the folder holds only one image
- **THEN** the hero shows that image without position dots and without click zones

### Requirement: Automatic crossfade every 13 seconds
With two or more images the hero SHALL crossfade to the next image 13 seconds after the last change, wrapping from the last image to the first. Hovering the hero SHALL NOT pause it.

#### Scenario: Auto-advance
- **WHEN** a visitor stays on the first image for 13 seconds
- **THEN** the second image fades in over the first

#### Scenario: Manual change restarts the countdown
- **WHEN** the visitor changes image by a click zone, dot or arrow key
- **THEN** the next automatic change happens 13 seconds later

### Requirement: Click a side to change image
With two or more images, clicking or tapping the left half of the hero SHALL go to the previous image and the right half to the next image, wrapping around, using the same crossfade. Hovering a half SHALL show a faint arrow at that edge.

#### Scenario: Next with the right half
- **WHEN** the visitor clicks the right half of the hero on the first image
- **THEN** the second image fades in

#### Scenario: Previous wraps around
- **WHEN** the visitor clicks the left half on the first image
- **THEN** the last image fades in

#### Scenario: Vertical scroll on a phone
- **WHEN** the visitor swipes vertically on the hero on a touch screen
- **THEN** the page scrolls and the image does not change

### Requirement: Position dots with progress
With two or more images the hero SHALL show one dot per image. The active dot SHALL fill over 13 seconds. Clicking a dot SHALL show that image.

#### Scenario: Jump with a dot
- **WHEN** the visitor clicks the third dot
- **THEN** the third image fades in and the third dot becomes active

### Requirement: Keyboard and reduced motion
When focus is inside the hero, the ← and → keys SHALL go to the previous and next image. When the visitor prefers reduced motion, the hero SHALL NOT auto-advance or animate, but click zones, dots and keys SHALL still work.

#### Scenario: Reduced motion
- **WHEN** the operating system asks for reduced motion
- **THEN** the image does not change by itself
