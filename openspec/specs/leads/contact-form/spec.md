# leads/contact-form Specification

## Purpose
The form a visitor uses to ask D3 Studio for a consultation. It is placed on the project page and reused by the contact page, so that every visitor request becomes a lead with its context.

## Requirements

### Requirement: Short form with a personal-data notice
The contact form SHALL show at most 5 inputs: name (required), phone (required), email (optional), message (optional) and, only when the visitor accepted behaviour collection, an unticked box "Gửi kèm những không gian tôi đã xem". Above the button it SHALL say what the data is used for: a consultant contacts the visitor, and the data is not shared with third parties.

#### Scenario: Visitor who declined collection
- **WHEN** a visitor who chose "Không đồng ý" opens the form
- **THEN** they see name, phone, email and message, the personal-data notice, and no "send what I viewed" box

#### Scenario: Visitor who accepted collection
- **WHEN** a consented visitor opens the form
- **THEN** the "Gửi kèm những không gian tôi đã xem" box is shown and is not ticked

### Requirement: Errors next to the field, input kept
When the phone or email is malformed or the name is empty, the form SHALL show the error under that field before sending, and SHALL show any field error returned by the server the same way. The text already typed SHALL be kept.

#### Scenario: Wrong phone
- **WHEN** a visitor types phone "12345" and presses "Gửi"
- **THEN** "Số điện thoại chưa đúng" appears under the phone field, nothing is sent, and the other fields keep their text

### Requirement: Success and failure states
After a successful submission, the form SHALL be replaced by a confirmation that a consultant will call back, with the phone number the visitor gave. On a network error or a 429, it SHALL show a message, keep the input and let the visitor retry. The button SHALL be disabled while sending.

#### Scenario: Sent
- **WHEN** the server accepts the submission
- **THEN** the visitor sees "Đã nhận yêu cầu, tư vấn viên sẽ gọi lại số 0912345678"

#### Scenario: Too fast
- **WHEN** the server answers 429
- **THEN** the visitor sees "Bạn gửi quá nhanh, vui lòng thử lại sau ít phút", and the input is kept

### Requirement: Form carries its context
The form SHALL send the page it is on and, when embedded for a project or space, that project's slug or that space's id, so the lead shows where the request came from. It SHALL be usable on any page without changes to the form itself.

#### Scenario: Embedded on the contact page
- **WHEN** the form is embedded on `/lien-he` without a project
- **THEN** the lead's context is the page `/lien-he` with no project

### Requirement: Usable on a phone and by keyboard
Every input SHALL have a visible label. Phone and email SHALL use the matching keyboard type. The form SHALL fit at 360px without horizontal scroll. Errors and the confirmation SHALL be announced to screen readers.

#### Scenario: Phone width
- **WHEN** the form is shown at 360px
- **THEN** the fields are stacked full width and there is no horizontal scroll
