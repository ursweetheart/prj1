# leads/lead-intake Specification

## Purpose
How a potential customer (lead) enters the system from any source: the contact form, the assistant handoff, and later the brief and the estimate. Covers validation, spam protection, the consented behaviour profile, notifications, and how sales staff see the lead. Following up a lead happens outside the system.

## Requirements

### Requirement: Create a lead from the contact form
The public endpoint `POST /leads` SHALL create a lead with source `form` from a name, a phone number, an optional email, an optional message and the visitor's context (page path, and project slug or space id when present). It SHALL return the lead id and a confirmation message.

#### Scenario: Valid submission on a project page
- **WHEN** a visitor submits name "Lan", phone "0912345678" and message "Căn hộ 70m2" from `/du-an/du-an-mau-01`
- **THEN** the response is 201 with the lead id, and the stored lead has source `form`, those fields, and the context page `/du-an/du-an-mau-01` and project `du-an-mau-01`

#### Scenario: No email and no message
- **WHEN** a visitor submits only name and phone
- **THEN** the lead is created with empty email and message

### Requirement: Validate contact data
`POST /leads` SHALL reject the request with 422 and a per-field Vietnamese message when the name is empty, the phone is not a Vietnamese number (`0` or `+84` followed by 9 digits, spaces and dots ignored), the email is malformed, or the message is longer than 1000 characters. No lead SHALL be stored for a rejected request.

#### Scenario: Wrong phone format
- **WHEN** a visitor submits phone "12345"
- **THEN** the response is 422 naming the phone field, and no lead is stored

#### Scenario: Phone written with spaces
- **WHEN** a visitor submits phone "+84 912 345 678"
- **THEN** the lead is stored with phone "0912345678"

### Requirement: Block automated submissions
`POST /leads` SHALL allow at most 5 submissions per client per 10 minutes and answer 429 beyond that. It SHALL silently drop a submission whose hidden honeypot field is filled, or that arrives less than 3 seconds after the form was shown. A dropped submission SHALL get the same success response as a real one and SHALL NOT store a lead or send a notification.

#### Scenario: Bot fills the hidden field
- **WHEN** a submission has the honeypot field set
- **THEN** the response looks successful, but no lead is stored and nobody is notified

#### Scenario: Too many submissions
- **WHEN** the same client submits a sixth time within 10 minutes
- **THEN** the response is 429 with a Retry-After header

### Requirement: Consented behaviour profile on the lead
A lead SHALL carry a behaviour profile only when the visitor accepted behaviour collection on the consent banner and also asked, on the form, to send what they viewed. The profile SHALL be a snapshot taken when the lead is created: the spaces viewed in that session (at most 12, most recent first) and the most frequent facet values across them. Without both consents the lead SHALL have no profile and no session link.

#### Scenario: Consented visitor sends their views
- **WHEN** a visitor who accepted collection and viewed 4 published spaces (3 tagged `Wabi_sabi`) ticks "gửi kèm những không gian tôi đã xem" and submits
- **THEN** the lead's profile lists those 4 spaces, and `phong_cach:Wabi_sabi` (3) is its top value

#### Scenario: Visitor declined collection
- **WHEN** a visitor who chose "Không đồng ý" submits the form
- **THEN** the lead has no profile and no session id, even if the request carries a session id

#### Scenario: Consent given but box not ticked
- **WHEN** a consented visitor submits without ticking the box
- **THEN** the lead has no profile

### Requirement: One intake for every source
Every lead, whatever its source, SHALL be created through the same intake with a source value (`form`, `chat`, and later `brief`, `estimate`). The intake SHALL apply the same profile rule and the same notification. A chat handoff SHALL be stored with source `chat`, its intent, its parsed request and its conversation.

#### Scenario: Chat handoff with consent
- **WHEN** a consented visitor's chat question cannot be answered and they agreed to send their views
- **THEN** a lead with source `chat`, intent `handoff`, the conversation and a behaviour profile is stored, and the consultants are notified

#### Scenario: Existing chat leads
- **WHEN** the change is deployed on a database with earlier chat leads
- **THEN** those leads show source `chat` and keep their intent, request, conversation and contact

### Requirement: Notify consultants of a new lead
Creating a lead SHALL notify the consultants with the source, the contact data, the context and a one-line profile summary (for example "Wabi_sabi 60% · phòng khách · 4 không gian"). When outgoing mail is configured, this SHALL be an email to the sales address. Otherwise it SHALL be written to the server log. A notification failure SHALL NOT fail the visitor's request or lose the lead.

#### Scenario: Mail configured
- **WHEN** a lead is created and the sales mail address is configured
- **THEN** one email with the contact, context and profile summary is sent to that address

#### Scenario: Mail server down
- **WHEN** sending the email fails
- **THEN** the visitor still gets the success response, the lead is stored, and the failure is logged

### Requirement: Confirm to the visitor
When the visitor gave an email and outgoing mail is configured, the system SHALL send them a confirmation that their request was received and that a consultant will contact them, without repeating the behaviour profile.

#### Scenario: Visitor gave an email
- **WHEN** a lead with email "lan@example.com" is created and mail is configured
- **THEN** a confirmation email goes to "lan@example.com"

### Requirement: Sales staff see every lead
`GET /leads` (sales, lead architect, admin) SHALL list leads from all sources, newest first, with source, name, phone, email, message, context, profile, and, for chat leads, intent, request and conversation, and, for brief leads, house type, area, budget, the photo summary, the sent photos with their notes and the share code. It SHALL accept a `nguon` filter. The leads page SHALL show a source label, the contact data, a link to the project or space of the context, the profile summary with the viewed spaces, and for a brief its project facts, summary, photos with notes and share link.

#### Scenario: Form lead on the leads page
- **WHEN** a sales user opens `/khach-hang` after the "Lan" form lead was created
- **THEN** it is listed first with the label "Form liên hệ", the name, phone, message, a link to project `du-an-mau-01`, and its profile summary if it has one

#### Scenario: Visitor cannot list leads
- **WHEN** an anonymous visitor calls `GET /leads`
- **THEN** the response is 401

#### Scenario: Brief lead on the leads page
- **WHEN** a sales user opens `/khach-hang` after a brief with 3 photos was sent
- **THEN** it is listed with the label "Bộ sưu tập", the house type, area and budget, the summary line, the 3 photos with their notes, and a link to `/bo-suu-tap/xem/<ma>`

#### Scenario: Filter briefs
- **WHEN** a sales user picks the "Bộ sưu tập" filter
- **THEN** only leads with source `brief` are listed
