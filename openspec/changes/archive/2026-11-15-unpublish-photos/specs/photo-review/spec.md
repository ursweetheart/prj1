## ADDED Requirements

### Requirement: Take a published photo down
A lead architect or admin SHALL be able to take a published photo down, for one photo or a selection, all or nothing, with a reason of 5 to 500 characters, choosing the outcome:
- "Gỡ xuống để sửa" moves it to "Nháp";
- "Gỡ và lưu nội bộ" moves it to "Lưu nội bộ".

Only published photos SHALL be taken down. A selection containing any other status SHALL be refused with that photo named. Architects and content editors SHALL get 403, and anonymous requests 401.

#### Scenario: Take down to fix
- **WHEN** the lead architect takes a published photo down with the reason "Nhãn phong cách sai, cần sửa"
- **THEN** the photo is in "Nháp", and its card shows "Đã gỡ khỏi website: Nhãn phong cách sai, cần sửa"

#### Scenario: Client withdraws consent
- **WHEN** the lead architect takes two published photos down to internal with the reason "Khách rút lại đồng ý công bố"
- **THEN** both are in "Lưu nội bộ" and can only come back through "Mở lại"

#### Scenario: Mixed selection
- **WHEN** a take-down names two published photos and one draft
- **THEN** none of them moves and the error names the draft

#### Scenario: Architect tries
- **WHEN** an architect sends a take-down
- **THEN** the server answers 403

### Requirement: A take-down is logged, shown and told
A take-down SHALL be written to the review log with the user, time, status before and after, and the reason. The reason SHALL be shown on the photo's card until the photo is advanced again. The architect who uploaded each photo SHALL be told, one message per uploader, by email when email is configured and in the server log otherwise. A failed notice SHALL NOT undo the take-down.

#### Scenario: Uploader told
- **WHEN** the lead architect takes down a photo uploaded by an architect, with email not configured
- **THEN** the server log names that photo, "Gỡ khỏi website" and the reason

### Requirement: A taken-down photo leaves the public site
Right after a take-down the photo SHALL NOT appear on:
- its space page;
- the portfolio list;
- text or photo search;
- the project's spaces;
- the style quiz;
- the assistant's example photos;
- the spaces of an item;
- the project results;
- a visitor's saved collection;
- a sent brief.

If the photo is published again it SHALL reappear where it was saved or sent.

#### Scenario: Space page
- **WHEN** a visitor opens the page of a photo that was just taken down
- **THEN** the page answers "not found"

#### Scenario: Saved by a visitor
- **WHEN** a visitor had saved the photo and it is taken down
- **THEN** it is no longer in their saved list, and it returns if the photo is published again

### Requirement: Returning still refuses published photos
"Trả về nháp" SHALL keep refusing published photos. Taking a published photo down SHALL only happen through the take-down action and its own wording.

#### Scenario: Return a published photo
- **WHEN** a return names a published photo
- **THEN** the server answers 409 and the photo stays published
