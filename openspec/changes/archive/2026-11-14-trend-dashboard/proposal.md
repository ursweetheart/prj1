# Proposal

## Why

QT-06 in the diagrams is the "AI reads behaviour" half of the project (act-3, seq-4, seq-18, dfd-2-5, BFD 5.1–5.2): consented interactions are enriched with the design attributes of what was seen, scored as an interest per attribute, compared with a 4-week moving average, and shown to the sales manager on a dashboard, so leadership can pick new concepts and marketing topics. Today the site collects consented views (`su_kien`) and now also saves, briefs and estimates, but nobody can see any of it: there is no dashboard (UC22) and no interest score.

The real data is still tiny (one day, a few dozen views), so a dashboard alone would be blank in a demo. This change adds a clearly labelled, removable demo-activity generator next to it.

## What Changes

- **Saves become behaviour signals.** Saving a photo with the heart sends a consented event `luu_anh` with the space's taxonomy snapshot, the same way views do. Without consent only the day's anonymous count moves.
- **Interest score (Điểm quan tâm) per taxonomy value,** over a chosen period: views × 1 + saves × 3 + photos sent in a brief × 5. Shown as the value's share of its dimension.
- **Trend per value.** The last 7 days are compared with the average of the 4 weeks before. A value is marked "đang tăng" or "đang giảm" when it moves by ≥ 50% with enough activity behind it (at least 5 signals), and those values are listed as trend alerts.
- **A dashboard `/quan-tri/xu-huong`** for sales and the lead architect / admin, with a period of 7, 30 or 90 days:
  - totals: views, with the share that is consented; saves; briefs; leads by source;
  - per dimension (style, colour tone, material, space type, layout…), the ranked values with score bar, share and trend arrow;
  - the trend alerts;
  - leads by source per week for 8 weeks;
  - the 5 most viewed spaces.
  
  It uses plain CSS bars, with no chart library.
- **Demo activity:** `python -m pipeline.demo_activity` creates consented-looking sessions over the last 8 weeks, including one rising style, with ids starting `demo-`. `--remove` deletes them. While any exist, the dashboard says "Đang hiển thị cả dữ liệu mô phỏng", and taxonomy discovery ignores them.

## Capabilities

### New Capabilities
- `analytics/interest-score`: which signals count and with what weight, the score and share per taxonomy value, the trend against the 4-week average, and the alert rule. Also covers save events.
- `analytics/trend-dashboard`: the staff page, who may see it, the period, and its sections.
- `analytics/demo-activity`: generating and removing labelled demo behaviour, its banner, and its exclusion from taxonomy discovery.

### Modified Capabilities
None. View events stay as `taxonomy/candidate-signals` describes them; this change only reads them and adds one more consented event type.

## Impact

- **Backend:** `backend/schema.sql` (`su_kien.loai` allows `luu_anh`), `backend/api.py` (`/events` accepts `luu_anh`; `GET /analytics/overview`), new `backend/pipeline/trends.py`, new `backend/pipeline/demo_activity.py`, `backend/pipeline/discovery.py` (skips `demo-` sessions), and new `backend/tests/test_trends.py`.
- **Frontend:** `src/api.js` (`trackSave`, `getOverview`), `src/lib/collection.js` (send `luu_anh` on add), new `src/views/TrendsView.vue`, `src/router/index.js`, and `src/components/SiteNav.vue` (role link "Xu hướng").
- **Out of scope (v2):** the weekly email report (Monday 8h, seq-18) and its scheduler, session clustering for new taste groups (act-3), an analytics warehouse or nightly roll-ups (v1 computes on request, which is fine at this size), per-project performance for architects (BFD 5.4), and search or filter events.
