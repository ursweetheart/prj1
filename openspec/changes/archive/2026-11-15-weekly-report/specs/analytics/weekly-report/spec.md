## Purpose

Sends the sales manager, the lead architect and admin a weekly email with what visitors did last week, how it compares with the week before, the trend alerts, and the projects that need attention (UC23; seq-18 steps 1–7), so they do not have to remember to open the dashboards.

## ADDED Requirements

### Requirement: Report content
The weekly report SHALL cover the last full week (Monday to Sunday, Vietnam time) and SHALL contain:
- views, saves, briefs sent and leads by source, each with the change from the week before;
- the trend alerts, as the trend dashboard computes them;
- the top 3 styles and space types by interest score;
- the "Cần xem lại" projects with their 30-day views;
- links to the trend dashboard and the project results page.

#### Scenario: Totals compared with the week before
- **WHEN** consenting visitors viewed photos 120 times last week and 100 times the week before
- **THEN** the report shows 120 views and "+20%"

#### Scenario: No earlier activity
- **WHEN** there were saves last week and none the week before
- **THEN** the report shows the saves without a percentage, marked as new

#### Scenario: Nothing to flag
- **WHEN** there are no trend alerts and no project is "Cần xem lại"
- **THEN** each of those sections says there is nothing to report, rather than being left out

### Requirement: Report holds no personal data
The report SHALL contain only counts, never a visitor's name, contact, account or session id. While simulated demo activity exists, the report SHALL say so at the top.

#### Scenario: A lead last week
- **WHEN** a visitor left their name and phone number in a lead last week
- **THEN** the report counts the lead under its source and shows neither the name nor the number

#### Scenario: Demo data loaded
- **WHEN** demo sessions exist at send time
- **THEN** the report starts with a note that it includes simulated data

### Requirement: Weekly schedule, once per week
The system SHALL build and send the report automatically on Monday from 08:00 Vietnam time (UTC+7), at most once per week, even when the server restarts. If the server was not running at 08:00 Monday, the report SHALL be sent at the first check later in that same week. Weeks missed entirely SHALL NOT be sent afterwards. An administrator SHALL be able to turn the schedule off by configuration.

#### Scenario: Restart after sending
- **WHEN** the report for this week was sent and the server restarts on Monday at 09:00
- **THEN** no second report is sent for that week

#### Scenario: Server down on Monday morning
- **WHEN** the server starts on Tuesday at 10:00 and this week's report was not sent
- **THEN** the report is sent shortly after it starts

#### Scenario: Before Monday 08:00
- **WHEN** the check runs on Monday at 07:30
- **THEN** nothing is sent yet

### Requirement: Recipients and opt-out
The report SHALL go to every account whose role is sales, lead_architect or admin, which is not locked, and which has not turned the report off. Each recipient SHALL get a separate email, so no recipient sees another's address. Accounts with a placeholder address that cannot receive mail SHALL be skipped. Each of these users SHALL be able to turn the report off and on for themselves, and the email SHALL say where.

#### Scenario: Locked and opted-out accounts
- **WHEN** one sales account is locked and one lead architect turned the report off
- **THEN** neither receives the report, and the other sales, lead architect and admin accounts do

#### Scenario: Visitor cannot subscribe
- **WHEN** a visitor or architect tries to turn the weekly report on for themselves
- **THEN** the server answers 403

### Requirement: Sending without email configured
When outgoing email is not configured, the report SHALL be written to the server log instead and recorded as "chỉ ghi log", and it SHALL still count as this week's report. A failure to send to one recipient SHALL NOT stop the others, and SHALL be counted in the record.

#### Scenario: No SMTP
- **WHEN** the scheduled time passes and no mail server is configured
- **THEN** the report text appears in the log and the week is recorded as "chỉ ghi log"

### Requirement: Send log, preview and test send
Admin and the lead architect SHALL see the last 8 weekly reports, with:
- the week;
- when it was sent;
- the number of recipients;
- the number of failures;
- the result.

They SHALL be able to preview this week's report without sending it, and to send a test copy only to themselves. A test copy SHALL NOT count as the week's report. Other roles SHALL get 403, and anonymous requests 401.

#### Scenario: Test send
- **WHEN** the lead architect presses "Gửi thử cho tôi" on Monday before 08:00
- **THEN** only they receive the report, and the scheduled report still goes to everyone at 08:00

#### Scenario: Sales cannot read the log
- **WHEN** a sales user requests the report log
- **THEN** the server answers 403
