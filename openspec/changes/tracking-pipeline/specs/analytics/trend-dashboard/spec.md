## ADDED Requirements

### Requirement: Data freshness
The dashboard SHALL show the last day included in its figures, "Số liệu đến hết ngày <date>", and when no day has been processed yet it SHALL say so instead of showing empty rankings.

#### Scenario: Before the first nightly run
- **WHEN** the dashboard is opened before any day was processed
- **THEN** it says "Chưa có số liệu tổng hợp: tiến trình hằng đêm chưa chạy"

### Requirement: Taste groups section
The dashboard SHALL list the taste groups of the latest run, each with its share of sessions, its defining values by name and a "mới" badge when new. It SHALL say so when there was too little data.

#### Scenario: New group shown
- **WHEN** the latest run found a new group led by Japandi and `mau_sac:xanh_reu`
- **THEN** the section lists it with "mới", its share and "Japandi · Xanh rêu …"

### Requirement: Homepage suggestion controls
Each value in the rankings and alerts SHALL offer the homepage setting of `analytics/home-suggestions` ("Tự động", "Ưu tiên", "Ẩn"), and the dashboard SHALL show the current homepage selection.

#### Scenario: Setting from an alert
- **WHEN** the sales manager picks "Ưu tiên" on the Wabi-sabi alert
- **THEN** the setting is saved and the homepage preview starts with Wabi-sabi spaces
