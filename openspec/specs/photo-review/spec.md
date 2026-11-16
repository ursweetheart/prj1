# photo-review Specification

## Purpose
The backward paths of photo review (QT-01; act-1, seq-6): the lead architect can send a photo back to draft or keep it internal, always with a reason that is shown, logged and sent to the architect who uploaded it.

## Requirements

### Requirement: Return to draft with a reason
A lead architect or admin SHALL be able to return a photo that is "Chờ duyệt", "Đã duyệt" or "Đã xác nhận quyền" to "Nháp", with a reason of 5 to 500 characters. The return SHALL work for one photo or for a selection, all or nothing. A published photo, a draft or an internal photo SHALL NOT be returned.

#### Scenario: Return one photo
- **WHEN** the lead architect returns a photo in "Chờ duyệt" with the reason "Nhãn phong cách sai, đây là Japandi"
- **THEN** the photo is in "Nháp" and its card shows "Bị trả về: Nhãn phong cách sai, đây là Japandi"

#### Scenario: Missing reason
- **WHEN** a return is sent with the reason "sai"
- **THEN** the server answers 422 and the photo does not move

#### Scenario: A selection with a published photo
- **WHEN** a return names three photos and one of them is published
- **THEN** none of them moves and the error names the published photo

### Requirement: Who may return
Returning, keeping internal and reopening SHALL be limited to the lead architect and admin roles. Architects and content editors SHALL get 403, and anonymous requests 401.

#### Scenario: Architect tries to return
- **WHEN** an architect sends a return for a photo in "Chờ duyệt"
- **THEN** the server answers 403 and the photo stays where it is

### Requirement: Keep internal
A lead architect or admin SHALL be able to mark a photo in "Đã duyệt" or "Đã xác nhận quyền" as "Lưu nội bộ" with a reason. A photo kept internal SHALL never appear on public pages, in search or in suggestions, and SHALL NOT be advanced. "Mở lại" SHALL send it back to "Nháp" with a reason.

#### Scenario: Client refuses
- **WHEN** the lead architect keeps an approved photo internal with the reason "Khách không đồng ý công bố"
- **THEN** it is listed under the "Lưu nội bộ" chip with that reason, and a request to advance it answers 409

#### Scenario: Not public
- **WHEN** a visitor asks for that photo's page or searches for it
- **THEN** it is not found or not listed

#### Scenario: Reopen
- **WHEN** the lead architect reopens it with the reason "Khách đã đồng ý lại"
- **THEN** it is a draft again, with that reason on its card

### Requirement: The reason is shown until the photo moves on
The latest return, keep-internal or reopen reason SHALL be shown on the photo's card in the review queue, with who gave it and when. It SHALL stop being shown once the photo is advanced again. Every reason SHALL stay in the review log with its user, time, the status before and the status after.

#### Scenario: Fixed and resubmitted
- **WHEN** the architect fixes the returned photo and sends it to review again
- **THEN** its card no longer shows the reason, and the review log still holds the return with its reason

### Requirement: The uploader is told
After a return, keep-internal or reopen, the system SHALL notify the architect who uploaded each photo: one message per uploader, listing the photos and reasons, sent by email when email is configured and written to the server log otherwise. A failed notice SHALL NOT undo the change. In the "Nháp" view a reviewer SHALL be able to show only returned drafts.

#### Scenario: Two photos from one architect
- **WHEN** the lead architect returns two photos uploaded by the same architect
- **THEN** that architect gets one message naming both photos and their reasons

#### Scenario: Only returned drafts
- **WHEN** an architect ticks "Chỉ ảnh bị trả về" in the "Nháp" view
- **THEN** only drafts with a shown return reason are listed

### Requirement: Reason entry is accessible
The reason SHALL be entered in a dialog with a labelled text field, a character count and the error next to the field. The dialog SHALL be usable by keyboard (Esc cancels, focus returns to the button that opened it), and on a 360px screen without sideways scroll.

#### Scenario: Keyboard
- **WHEN** a reviewer opens "Trả về nháp" with Enter, types a reason and presses Esc
- **THEN** the dialog closes, nothing is returned and focus is back on "Trả về nháp"

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
