# Spec Delta

## Purpose

Lets a visitor send their saved collection to an architect as a design brief ("phiếu yêu cầu thiết kế"), so the consultant receives the photos the visitor chose, their notes, their project facts and a summary of their taste, as one lead.

## ADDED Requirements

### Requirement: Brief form
"Gửi cho kiến trúc sư" on the collection page SHALL open a form with: name (required), phone (required), email (optional), house type (Căn hộ / Chung cư, Nhà phố, Biệt thự, Văn phòng, Thương mại / Showroom, Khác), area in m² (optional, 10–5000), budget (the four budget ranges of the taxonomy, or "Chưa rõ") and a note (optional, ≤ 1000 characters), with the same personal-data notice as the contact form. It SHALL list how many photos will be sent.

#### Scenario: Open the form
- **WHEN** a visitor with 5 saved spaces presses "Gửi cho kiến trúc sư"
- **THEN** the form shows the fields above and "5 ảnh trong bộ sưu tập sẽ được gửi kèm"

### Requirement: Anyone can send a brief
Sending a brief SHALL NOT require an account. It SHALL require at least one saved published space and SHALL use the same contact validation, spam protection and rate limit as the contact form (one shared limit of 5 submissions per 10 minutes per client).

#### Scenario: Anonymous visitor sends
- **WHEN** an anonymous visitor with 3 saved spaces fills name, phone "0912345678", house type "Căn hộ / Chung cư", area 70 and sends
- **THEN** the response is 201 and a lead with source `brief` exists

#### Scenario: Empty collection
- **WHEN** a brief is submitted with no published space
- **THEN** the response is 422 and no lead is stored

### Requirement: Brief keeps the photos as sent
A sent brief SHALL keep its own copy of the photos and notes as they were at sending, with a share code. Later changes to the visitor's collection SHALL NOT change a sent brief. The visitor's collection SHALL stay as it is after sending.

#### Scenario: Visitor keeps editing
- **WHEN** a visitor sends a brief with spaces 21 and 22, then removes 22 from their collection
- **THEN** the brief's shared view still shows 21 and 22

### Requirement: Summary of the chosen photos
The brief lead SHALL carry a summary computed from the taxonomy tags of the sent photos: the leading style and its share of the photos, the recurring colour tone, and the most frequent space types, as one line (e.g. "Wabi-sabi 60% · tông Ấm · phòng khách, bếp & phòng ăn"). Values tagged `khac` SHALL be left out. Because the visitor chose these photos to send, this summary SHALL NOT depend on the behaviour-collection consent.

#### Scenario: Five photos
- **WHEN** a brief is sent with 5 photos, 3 tagged `phong_cach:Wabi_sabi`, 4 tagged `tong_mau:warm`, 3 tagged `khong_gian:phong_khach`
- **THEN** the summary is "Wabi-sabi 60% · tông Ấm · phòng khách"

### Requirement: Brief lead through the intake
The brief SHALL create its lead through the shared lead intake with source `brief`: the contact data, the house type, area, budget and note, the summary, the link to the sent copy, and, under the same double-consent rule as other leads, the behaviour profile. The consultants SHALL be notified with the summary and the share link, and a visitor who gave an email SHALL get a confirmation that includes the share link.

#### Scenario: Notice to sales
- **WHEN** a brief is sent and mail is configured
- **THEN** the sales email names the source "Bộ sưu tập (brief)", the house type, area, budget, the summary and the share link `/bo-suu-tap/xem/<ma>`

#### Scenario: Confirmation to the visitor
- **WHEN** a brief with email "lan@example.com" is sent and mail is configured
- **THEN** the confirmation to "lan@example.com" includes the share link and no behaviour profile

### Requirement: After sending
After a successful brief the form SHALL be replaced by a confirmation naming the phone number and offering the share link to view or copy. Errors SHALL be shown as on the contact form, keeping the input.

#### Scenario: Sent
- **WHEN** the server accepts the brief
- **THEN** the visitor sees "Đã gửi bộ sưu tập cho kiến trúc sư, tư vấn viên sẽ gọi lại số 0912345678" and a link to the shared view
