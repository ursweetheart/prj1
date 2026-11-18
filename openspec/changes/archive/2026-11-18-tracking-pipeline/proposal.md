# Proposal

## Why

The behaviour-tracking diagrams (seq-4, act-3, act-7, dfd-2-1, dfd-2-5, seq-2, class-4) describe a pipeline the backend only partly builds. Events are sent one at a time, there is no nightly processing or analytics store, no session clustering, no way to change consent or delete one's data, no search events, and the leadership cannot act on trends from the homepage. The team decided the code must match the diagrams, so this change builds the missing parts.

## What Changes

- **Consent (act-7):** the banner offers Đồng ý / Từ chối / Tùy chỉnh. Tùy chỉnh lets the visitor choose analytics and personalisation separately. A footer link reopens the choice, and a visitor can delete the data collected about their browser.
- **Browser collector (seq-4 steps 1-3, act-3):** events are buffered in the browser and sent as one batch every 5 seconds and when the page is left. The batch carries the session's anonymous device id, traffic source and device type (class-4 PhienTruyCap). Each event keeps the time it happened.
- **Collector (seq-4 steps 4-5):** `POST /events` takes a batch, validates every event and the consent state, and appends the events to the raw store. It also records the session's start and end and the object type of each event (class-4 SuKien).
- **Search events (dfd-2-1 1.3, seq-2 steps 12 and 14):** searching by photo or description, showing similar spaces, and opening one of those suggestions are recorded.
- **Nightly processing (seq-4 steps 6-11, act-3, dfd-2-5 5.2/5.3):** once a night, the previous days' raw events are:
  - enriched with design attributes;
  - given a real dwell time;
  - checked for abnormal sessions, which are dropped;
  - aggregated per attribute and per day into an analytics store (fact tables over the taxonomy dimensions).

  The interest scores, trend index and trend alerts are then computed and stored.
- **Taste groups (act-3):** the nightly job clusters consented sessions by the design attributes they engaged with, and flags groups that are new.
- **Dashboard and report read the analytics store (seq-4 steps 12-15, seq-18):** the trend dashboard and weekly report show stored figures up to the last nightly run, plus the new taste-group section, search figures and the data's freshness.
- **Homepage suggestions (act-3 "Điều chỉnh gợi ý trên trang chủ"):** leadership can prioritise or hide taxonomy values for a new "Đang được quan tâm" section on the homepage, which otherwise follows the trends. With personalisation consent it also favours what the visitor viewed.
- **BREAKING:** the dashboard no longer counts today's events until the nightly run. `POST /events` keeps accepting the single-event body for old clients.

## Capabilities

### New Capabilities
- `analytics/data-consent`: the three-way consent choice, changing it later, and deleting one's collected data.
- `analytics/analytics-store`: the nightly processing (enrichment, real dwell time, abnormal sessions, daily aggregates, stored scores and trend alerts) and what reads from it.
- `analytics/taste-groups`: nightly clustering of sessions into taste groups and flagging new ones.
- `analytics/home-suggestions`: the homepage "Đang được quan tâm" section driven by trends, leadership adjustments and personalisation.

### Modified Capabilities
- `analytics/behaviour-events`:
  - batching with event times;
  - session device, source and start / end;
  - each event's object type;
  - search, similar-shown and suggestion-accepted events;
  - search figures in the behaviour section.
- `analytics/trend-dashboard`: figures come from the analytics store with a "data up to" date; the new taste-group section; homepage-suggestion controls.
- `analytics/demo-activity`: generating or removing demo activity also refreshes the analytics store, so the dashboard shows the change at once.

## Impact

- **Backend:**
  - `api.py`: `/events` batch, consent / deletion endpoint, homepage suggestions endpoints, nightly scheduler next to the weekly one;
  - new `pipeline/rollup.py` (nightly job) and `pipeline/taste_groups.py` (scikit-learn k-means, already a dependency);
  - `pipeline/trends.py`, `pipeline/behaviour.py` and `pipeline/weekly_report.py` read the store;
  - `pipeline/demo_activity.py`;
  - `schema.sql`: new store tables, session and event columns, homepage settings, deletion log.
- **Frontend:**
  - `src/api.js`: batching collector, consent helpers, search / similar tracking;
  - `ConsentBanner.vue`, `pageTracking.js`, `TrendsView.vue`;
  - the consent call sites (`ChatWidget`, `BriefForm`, `ContactForm`, `EstimateView`);
  - new `TrendingSpaces.vue`;
  - `SiteFoot.vue`: one link;
  - `HomeView.vue`: one line, approved by the user for this change.
- **Not changed:**
  - Tùng's `SpaceView` / `SpacesView`: search events are hooked in `api.js`.
  - Interest-score weights and trend thresholds.
  - Lead behaviour profiles, which still read the session's raw events.
