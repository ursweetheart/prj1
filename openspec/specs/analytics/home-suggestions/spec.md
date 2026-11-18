# analytics/home-suggestions Specification

## Purpose
TBD - created by archiving change tracking-pipeline. Update Purpose after archive.

## Requirements

### Requirement: "Đang được quan tâm" on the homepage
The homepage SHALL show a section "Đang được quan tâm" with up to 8 published spaces. Each space SHALL carry the value it was chosen for, such as "Phong cách Wabi-sabi đang được quan tâm", and link to its space page. Values are taken in this order:
1. values the leadership prioritised;
2. values with a stored "đang tăng" or "mới nổi" trend;
3. the highest-scoring values of the last 30 days.

Each value contributes at most 2 spaces, with its most viewed published spaces first. Hidden values and `khac` values SHALL never be used. The section SHALL NOT appear when the backend does not answer or when there is no published space to show.

#### Scenario: Rising style
- **WHEN** Wabi-sabi is "đang tăng" and nothing is prioritised
- **THEN** the section starts with 2 Wabi-sabi spaces labelled "Phong cách Wabi-sabi đang được quan tâm"

#### Scenario: Backend off
- **WHEN** the site runs without the backend
- **THEN** the homepage shows no empty section and no error

### Requirement: Leadership adjusts the suggestions
On the trend dashboard, users who may see it SHALL be able to set each listed value to "Ưu tiên trên trang chủ", "Ẩn khỏi trang chủ" or back to automatic. They SHALL see a preview of what the homepage section currently shows. Every change SHALL take effect at once, be logged with who made it and when, and others SHALL get 403.

#### Scenario: Prioritise a value
- **WHEN** the sales manager sets Indochine to "Ưu tiên trên trang chủ"
- **THEN** the homepage section starts with Indochine spaces on its next load, and the log records the change

#### Scenario: Hide a value
- **WHEN** the lead architect hides "Luxury" while it is rising
- **THEN** no space is chosen for Luxury, even though it is rising

### Requirement: Personalised with consent
When a visitor allowed personalisation, the section SHALL put first the values most frequent in their own session's views, ahead of the trend order and behind prioritised values. Without that consent, the request SHALL carry no session id and the section SHALL be the same for everyone.

#### Scenario: Visitor viewed Indochine
- **WHEN** a visitor with personalisation consent viewed 4 Indochine spaces this session and nothing is prioritised
- **THEN** their section starts with Indochine spaces they have not viewed yet

#### Scenario: Analytics only
- **WHEN** a visitor allowed analytics but not personalisation
- **THEN** their section is the same as for a visitor who declined
