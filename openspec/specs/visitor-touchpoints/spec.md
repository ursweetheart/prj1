# visitor-touchpoints Specification

## Purpose
TBD - created by archiving change visitor-touchpoints. Update Purpose after archive.

## Requirements

### Requirement: Sign-up prompt after saving while signed out
When a signed-out visitor saves a photo with the heart, the page SHALL show "Đã lưu vào bộ sưu tập. Đăng ký để không mất bộ sưu tập" with a link to sign up that returns to the current page (seq-13 step 3). The note SHALL be shown at most once per browser session and announced to screen readers. Signed-in visitors SHALL NOT see it.

#### Scenario: First save
- **WHEN** a signed-out visitor saves their first photo
- **THEN** the note with the sign-up link appears

#### Scenario: Second save
- **WHEN** they save another photo in the same session
- **THEN** no note appears

### Requirement: Share a saved collection
`/bo-suu-tap` SHALL offer "Chia sẻ bộ sưu tập" when the collection has photos (BFD 2.3). It SHALL create a read-only snapshot of the current photos with a random code, and copy its link. The link opens the existing shared-collection page. Only published photos SHALL be included, at most 60. Later changes to the collection SHALL NOT change a shared snapshot. Creating snapshots SHALL be rate-limited.

#### Scenario: Share
- **WHEN** a visitor with 5 saved published photos clicks "Chia sẻ bộ sưu tập"
- **THEN** a link `/bo-suu-tap/xem/<code>` is copied, and opening it shows those 5 photos read-only

### Requirement: Projects in the same budget range
The estimate result SHALL list up to 3 published projects (seq-9 steps 6-7, act-6):
- whose investment level overlaps the estimated cost range, preferring the same building type;
- when no project has an investment level overlapping the range, published projects of the same building type instead, under "Cùng loại công trình (chưa có dữ liệu ngân sách)".

Each SHALL link to its project page, or to its first published photo when it has no page.

#### Scenario: Budget data exists
- **WHEN** the estimate is 500-800 million and a published apartment project has the investment level "300 – 700 triệu"
- **THEN** that project is listed under "Dự án trong cùng khoảng ngân sách"

#### Scenario: No budget data
- **WHEN** no project has an investment level
- **THEN** up to 3 projects of the same type are listed under the fallback heading

### Requirement: Suggested projects on the quiz result
The quiz result SHALL show the up to 3 suggested projects with their name, style and photo, each linking to its project page or photo (seq-12 steps 12-15).

#### Scenario: Result
- **WHEN** a visitor finishes the quiz with Japandi first
- **THEN** below the style, up to 3 projects with Japandi photos are shown as links

### Requirement: Working hours for chat hand-offs
Working hours SHALL be configurable, with a default of Monday to Saturday, 08:00 to 17:30, UTC+7. When the chat creates a lead (act-4):
- inside working hours, the team SHALL be notified at once;
- outside them, the visitor's answer SHALL say when they can expect contact ("Đội tư vấn sẽ liên hệ anh/chị từ 08:00 thứ Hai"), and the team notification SHALL be sent at the start of the next working period.

A notification due while the server was off SHALL be sent at the next check.

#### Scenario: Saturday night
- **WHEN** a visitor leaves their number in the chat at 21:00 on Saturday
- **THEN** the chat says the team will contact them from 08:00 Monday, and the team email goes out at 08:00 Monday

#### Scenario: Tuesday morning
- **WHEN** the same happens at 10:00 on Tuesday
- **THEN** the team is notified at once and no expected time is shown

### Requirement: SMS confirmations
When a visitor gives a phone number with a form, a brief or an estimate request, the confirmation SHALL also be sent by SMS if an SMS provider is configured (seq-5 step 11, seq-7 step 9, act-8). Every SMS attempt SHALL be recorded:
- the masked number;
- the message;
- sent / not configured / failed;
- the time.

Without a provider, nothing is sent and the attempt is recorded as not configured. The SMS SHALL carry no data beyond the confirmation and the collection link.

#### Scenario: Provider not configured
- **WHEN** a visitor sends the contact form with their phone and no SMS provider is set
- **THEN** the form succeeds, and the SMS log has one "not configured" row with the number masked
