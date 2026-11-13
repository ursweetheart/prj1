# Spec Delta

## Purpose

Lets the team demonstrate the trend dashboard before the site has weeks of real traffic, without letting invented data pass as real or leak into other features.

## ADDED Requirements

### Requirement: Generate labelled demo activity
`python -m pipeline.demo_activity` SHALL create consented-looking sessions whose ids start with `demo-`, with view and save events on published spaces spread over the last 8 weeks, and with one style clearly rising in the last 2 weeks. It SHALL be repeatable without duplicating: running it again replaces the earlier demo activity.

#### Scenario: Generate
- **WHEN** an operator runs the generator on a database with published spaces
- **THEN** demo sessions and events exist over the last 8 weeks, and one style is "đang tăng" on the dashboard

### Requirement: Remove demo activity
`python -m pipeline.demo_activity --remove` SHALL delete every `demo-` session and its events, and nothing else.

#### Scenario: Remove
- **WHEN** an operator runs the remove command
- **THEN** no `demo-` session or event remains and real sessions are untouched

### Requirement: Never passed off as real
While any demo session exists, the dashboard SHALL show "Đang hiển thị cả dữ liệu mô phỏng". Taxonomy discovery SHALL ignore demo sessions when it scores candidates.

#### Scenario: Banner
- **WHEN** demo activity exists and a sales user opens the dashboard
- **THEN** the banner "Đang hiển thị cả dữ liệu mô phỏng" is shown

#### Scenario: Discovery
- **WHEN** taxonomy discovery computes the behaviour component of a candidate
- **THEN** events of `demo-` sessions are not counted
