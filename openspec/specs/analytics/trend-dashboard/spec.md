# analytics/trend-dashboard Specification

## Purpose
Shows the sales manager and the lead architect what visitors are interested in and how it is moving (UC22; seq-18 "Bảng điều khiển", act-3 "Cập nhật bảng điều khiển"), so they can choose concepts and marketing topics from evidence.

## Requirements

### Requirement: Who sees the dashboard
`/quan-tri/xu-huong` and `GET /analytics/overview` SHALL be available to sales, the lead architect and admin. Other roles SHALL get 403, anonymous callers 401, and the header SHALL show the "Xu hướng" link only to those roles.

#### Scenario: Visitor account
- **WHEN** a signed-in visitor calls `GET /analytics/overview`
- **THEN** the response is 403

### Requirement: Period
The dashboard SHALL offer the periods 7, 30 and 90 days (default 30) for the totals, rankings and top spaces. Trends SHALL always compare the last 7 days with the 4 weeks before.

#### Scenario: Change period
- **WHEN** a sales user picks "7 ngày"
- **THEN** totals and rankings are recomputed for the last 7 days, and the trend arrows do not change

### Requirement: Totals
The dashboard SHALL show, for the period: total views (consented plus anonymous) with the consented share, saves, briefs sent, and leads per source (form, chat, brief, estimate).

#### Scenario: Consented share
- **WHEN** the period has 300 consented and 100 anonymous views
- **THEN** it shows 400 views, "75% có đồng ý"

### Requirement: Ranking per dimension
For each taxonomy dimension shown to visitors, the dashboard SHALL list its values by interest score (up to 8), each with a bar proportional to its share, the share in percent, the counts of views, saves and brief photos, and its trend ("đang tăng", "đang giảm", "mới nổi" or the change in percent). A dimension with no activity SHALL say so instead of an empty list.

#### Scenario: Style ranking
- **WHEN** Wabi-sabi has the highest style score and is rising
- **THEN** it is listed first under "Phong cách" with the longest bar and an up arrow

### Requirement: Trend alerts
The dashboard SHALL list every value currently "đang tăng", "mới nổi" or "đang giảm", rising ones first, as "Cảnh báo xu hướng", with its dimension and change.

#### Scenario: Rising style shows up
- **WHEN** Wabi-sabi is rising by +140%
- **THEN** "Phong cách · Wabi-sabi · +140%" appears in the alerts

### Requirement: Leads per week and top spaces
The dashboard SHALL show leads per source for each of the last 8 weeks, and the 5 most viewed published spaces in the period with a link to each space page.

#### Scenario: Top space opens
- **WHEN** a user clicks the first top space
- **THEN** its space page `/khong-gian/<id>` opens

### Requirement: Usable on a phone
The dashboard SHALL fit at 360px without horizontal page scroll, with sections stacked.

#### Scenario: Phone width
- **WHEN** the dashboard is opened at 360px
- **THEN** there is no horizontal page scroll
