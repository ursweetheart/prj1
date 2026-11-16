## Purpose

Lets architects place, move and name the hotspots on a photo and link each one to an item in a shared furniture and materials library (seq-14; class-1 Hotspot and MonDo; roadmap 1.9), so the hotspots say what is really in the room and the spaces using an item can be found.

## ADDED Requirements

### Requirement: Edit hotspots by hand
On the review page, architects, the lead architect and admin SHALL be able to:
- add a hotspot by clicking on the photo;
- move a hotspot by dragging it or with the arrow keys;
- delete a hotspot;
- edit the name visitors see;
- link the hotspot to a library item.

Saving SHALL replace the photo's hotspots with the edited list. Content editors and visitors SHALL get 403.

#### Scenario: Add a missed lamp
- **WHEN** an architect clicks on a pendant lamp the detector missed, names it "Đèn thả" and saves
- **THEN** the photo has a new hotspot at that position named "Đèn thả" and marked as made by hand

#### Scenario: Move a misplaced point
- **WHEN** an architect drags the detected sofa point onto the sofa and saves
- **THEN** the point has its new position and keeps its detection confidence and its "AI" origin

### Requirement: Hotspots record their origin and stay valid
Every hotspot SHALL record whether the detector or a person created it. A detected hotspot SHALL keep its detection box and confidence through edits. Positions SHALL be within the photo (0 to 1 on each axis). A name SHALL be 1 to 120 characters. A photo SHALL have at most 30 hotspots. A link SHALL point to an existing item. Saving SHALL be logged in the photo's review log.

#### Scenario: Position outside the photo
- **WHEN** a save contains a point at x = 1.2
- **THEN** the server answers 422 and the photo's hotspots are unchanged

#### Scenario: Unknown item
- **WHEN** a save links a point to an item that does not exist
- **THEN** the server answers 422 and nothing is saved

### Requirement: Item library
Staff SHALL keep a library of items, each with:
- a name, unique regardless of case and accents;
- a type;
- a style;
- a material;
- a colour;
- a supplier;
- a staff note.

They SHALL be able to search the library, create an item from the hotspot editor without leaving the photo, and edit items on the library page. The library page SHALL show how many photos use each item.

#### Scenario: Create while tagging
- **WHEN** an architect types "Sofa vải lanh xám" in the item picker, which has no match, and creates it with type "Sofa", material "Vải" and colour "Xám"
- **THEN** the item is saved and linked to the point being edited

#### Scenario: Duplicate name
- **WHEN** someone creates "sofa vai lanh xam" while "Sofa vải lanh xám" exists
- **THEN** the server answers 409 naming the existing item

### Requirement: Deleting an item in use is refused
An item linked from any photo SHALL NOT be deleted. The answer SHALL say how many photos use it. An unused item SHALL be deleted.

#### Scenario: Item in use
- **WHEN** an architect deletes an item linked from 3 photos
- **THEN** the server answers 409 saying 3 photos use it, and the item stays

### Requirement: Spaces that use an item
The system SHALL list the photos whose hotspots link to an item. Visitors SHALL see only published photos and only the item's name and type. Staff SHALL see photos in every state. No public response SHALL contain an item's supplier or staff note.

#### Scenario: Visitor asks for an item's spaces
- **WHEN** an item is linked from one published photo and one draft, and a visitor requests its spaces
- **THEN** only the published photo is listed, and the response has no supplier or note

### Requirement: Visitors still see names only
Hand-placed hotspots SHALL appear on the visitor's space page like detected ones, showing only the name visitors see. The visitor's hotspot card SHALL NOT show the item's supplier, note, price or any sales action.

#### Scenario: Hand-placed point on a published photo
- **WHEN** a published photo gains a hand-placed point named "Đèn thả" linked to an item with a supplier
- **THEN** the visitor's space page shows a marker whose card reads "Đèn thả" and "Không gian tương tự", and the page's data has no supplier

### Requirement: Usable by keyboard and on a phone
The hotspot editor SHALL let a keyboard user add a point, select a point, move it with the arrow keys and delete it. The library page SHALL have no sideways scroll at 360px.

#### Scenario: Keyboard only
- **WHEN** an architect presses "Thêm điểm", then moves the new point with the arrow keys and saves
- **THEN** the point is saved at the position reached
