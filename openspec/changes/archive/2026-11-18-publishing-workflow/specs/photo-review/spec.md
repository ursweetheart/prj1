## MODIFIED Requirements

### Requirement: Return to draft with a reason
A lead architect or admin SHALL be able to return a photo that is "Chờ biên tập", "Chờ duyệt", "Đã duyệt" or "Đã xác nhận quyền" to "Nháp", with a reason of 5 to 500 characters. The return SHALL work for one photo or for a selection, all or nothing. A published photo, a draft or an internal photo SHALL NOT be returned.

#### Scenario: Return one photo
- **WHEN** the lead architect returns a photo in "Chờ duyệt" with the reason "Nhãn phong cách sai, đây là Japandi"
- **THEN** the photo is in "Nháp" and its card shows "Bị trả về: Nhãn phong cách sai, đây là Japandi"

#### Scenario: Return from editing
- **WHEN** the lead architect returns a photo in "Chờ biên tập" with a reason
- **THEN** the photo is in "Nháp" with that reason

#### Scenario: Missing reason
- **WHEN** a return is sent with the reason "sai"
- **THEN** the server answers 422 and the photo does not move

#### Scenario: A selection with a published photo
- **WHEN** a return names three photos and one of them is published
- **THEN** none of them moves and the error names the published photo
