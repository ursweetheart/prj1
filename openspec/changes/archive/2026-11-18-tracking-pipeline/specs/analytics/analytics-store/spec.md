## ADDED Requirements

### Requirement: Nightly processing of the previous days
Once a night (from 01:00, UTC+7), the system SHALL process every complete day of raw events not processed yet (seq-4 loop "Hằng đêm", dfd-2-5 5.2). Each day is processed in one transaction and recorded as processed. The run SHALL NOT process the current day. It SHALL be safe to run again, recomputing a day replaces that day's figures, and an operator SHALL be able to run it by hand for given days.

#### Scenario: Missed nights
- **WHEN** the server was off for 3 nights and starts at 10:00
- **THEN** the next run processes the 3 missing days, each once, and today stays unprocessed

#### Scenario: Re-run a day
- **WHEN** an operator reprocesses 2026-11-10
- **THEN** that day's figures are replaced, not added to

### Requirement: Enrichment with design attributes
During processing, an event about a space that carries no design attributes SHALL get that space's current taxonomy values (seq-4 step 7). A project view SHALL get the values of that project's published spaces. Values captured when the event happened SHALL be kept as they are.

#### Scenario: Project view
- **WHEN** a consented visitor viewed `/du-an/hanjadin-apartment`, whose published spaces are Japandi living rooms
- **THEN** after processing that event carries `phong_cach:Japandi` and `khong_gian:phong_khach`

### Requirement: Real dwell time
Processing SHALL give every event a real dwell time (seq-4 step 8):
- the time the browser measured, when it sent one;
- otherwise the time until the session's next event;
- in both cases at most 30 minutes.

The last event of a session without a measured time SHALL have none.

#### Scenario: Photo view followed by another
- **WHEN** a visitor viewed space 12 and their next event came 45 seconds later
- **THEN** that view's real dwell time is 45 seconds

### Requirement: Abnormal sessions are dropped
A session SHALL be marked abnormal and left out of every aggregate if, on a day, it:
- sent more than 500 events; or
- sent 60 or more events within one minute; or
- has at least 20 page or project views, all under one second.

Its raw events SHALL be kept, so the decision can be checked.

#### Scenario: Script hammering the site
- **WHEN** one session sent 80 view events in one minute
- **THEN** it is marked abnormal and none of its events count in that day's figures

### Requirement: Daily aggregates in the analytics store
For each processed day, the store SHALL hold (seq-4 steps 9-10, dfd-2-5 D10):
- per taxonomy value (`dimension:value`): photo views, saves, photos sent in briefs, distinct sessions and total real dwell time;
- per space: views and saves;
- per behaviour event type and page or object: count, total dwell time and total scroll depth;
- per search kind: count;
- similar suggestions shown and accepted.

Only consented, non-abnormal events SHALL be counted. Anonymous daily counts SHALL stay as they are recorded. The store SHALL hold no session id, account or contact data.

#### Scenario: Day totals
- **WHEN** on 2026-11-10 consented visitors made 30 views and 4 saves of Wabi-sabi spaces
- **THEN** the store's row for 2026-11-10 and `phong_cach:Wabi_sabi` has 30 views and 4 saves

### Requirement: Stored scores and trend alerts
After the daily aggregates, the run SHALL compute from the store, for the last processed day, every value's interest score over the last 7 days, the average weekly score of the 4 weeks before, its change and its trend label (seq-4 step 11, act-3). It SHALL store them, keeping one set per run date. Scores over the dashboard's 7, 30 or 90-day periods SHALL be summed from the daily aggregates when read. The weights, thresholds and labels SHALL be those of `analytics/interest-score`. The values marked "đang tăng", "mới nổi" or "đang giảm" SHALL be stored as that run's trend alerts.

#### Scenario: Alert stored
- **WHEN** the run of 2026-11-18 finds Wabi-sabi at +140% with 12 signals
- **THEN** a trend alert "đang tăng" for `phong_cach:Wabi_sabi` with +140% is stored for 2026-11-18

### Requirement: Readers use the store
The trend dashboard, the behaviour section and the weekly report SHALL read their figures from the analytics store (seq-4 steps 12-15, seq-18 steps 2-3). Their periods SHALL end with the last processed day, and they SHALL state that day. Lead behaviour profiles SHALL keep reading the session's own raw events.

#### Scenario: Today's views
- **WHEN** a consenting visitor views 5 photos today and a sales user opens the dashboard
- **THEN** the dashboard does not include them yet, and says "Số liệu đến hết ngày <yesterday>"
