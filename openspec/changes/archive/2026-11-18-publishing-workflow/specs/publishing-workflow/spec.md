## ADDED Requirements

### Requirement: Editing stage between draft and review
A photo SHALL move: Nháp (`draft`) → Chờ biên tập (`editing`) → Chờ duyệt (`in_review`) → Đã duyệt → Đã xác nhận quyền → Đã xuất bản (seq-6 steps 1-6). These roles move it:
- architects, lead architects and admins send a draft to editing;
- content staff, lead architects and admins send an editing photo to review;
- only lead architects and admins move it further, as today.

Content staff SHALL be able to edit the caption and alt text of photos in editing. Every move SHALL be logged as today.

#### Scenario: Architect hands over
- **WHEN** an architect sends a fully labelled draft forward
- **THEN** it is in "Chờ biên tập", not "Chờ duyệt"

#### Scenario: Content editor sends to review
- **WHEN** a content editor edits the caption of a photo in "Chờ biên tập" and sends it forward
- **THEN** it is in "Chờ duyệt"

#### Scenario: Architect cannot skip editing
- **WHEN** an architect tries to send a photo in "Chờ biên tập" forward
- **THEN** the server answers 403

### Requirement: Required dimensions before leaving draft
A draft SHALL leave "Nháp" only when every dimension marked required has a value on the photo (act-1 "Đủ các features bắt buộc?"). Otherwise the server SHALL answer 422 naming the missing dimensions, and the review card SHALL show them.

#### Scenario: Missing style
- **WHEN** a draft has no style and style is a required dimension
- **THEN** sending it forward fails with "Thiếu: Phong cách" and it stays in "Nháp"

### Requirement: Hand-over notifications
When photos move to "Chờ biên tập", the system SHALL email every active content-staff account (seq-6 step 4). When photos move to "Chờ duyệt", it SHALL email every active lead architect (step 7). Each email SHALL go out once per action, listing the photos and who sent them. Without email configured, the move SHALL still succeed and the skipped email SHALL be logged.

#### Scenario: Three photos to editing
- **WHEN** an architect sends 3 drafts forward in one action
- **THEN** each content editor receives one email listing the 3 photos

### Requirement: Publish date
When a photo becomes published, its publish date SHALL be set to that moment (seq-6 step 17, class-6 `ngay_xuat_ban`). The date SHALL be returned with the photo and shown on its review card. A photo taken down and published again SHALL get the new date.

#### Scenario: Publish
- **WHEN** the lead architect publishes a photo on 2026-11-20
- **THEN** its publish date is 2026-11-20 and the card shows "Đăng ngày 20/11/2026"

### Requirement: Published photos join the assistant's knowledge
Publishing a photo SHALL queue a task that writes a description of the photo and embeds it into the assistant's photo knowledge (seq-6 step 18). The description is built from the photo's caption, room type, style, other labels, materials, colours and items, and carries no price. The assistant SHALL find the photo from its next question on. Taking a photo down SHALL remove it from that knowledge.

#### Scenario: Published then asked about
- **WHEN** a Japandi living room is published and the task has run
- **THEN** the assistant's photo search can return it for "phòng khách Japandi"

#### Scenario: Taken down
- **WHEN** the photo is taken down
- **THEN** its description is removed and the assistant no longer returns it
