# Spec Delta

## MODIFIED Requirements

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
