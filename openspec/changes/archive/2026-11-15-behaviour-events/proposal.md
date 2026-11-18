# Proposal

## Why

UC21 (seq-4, act-7, dfd-2-5) lists the behaviour events the analytics need:

| Event | Meaning |
| :-- | :-- |
| `xem_trang` | page view |
| `xem_du_an` | project view |
| `phong_to_anh` | photo zoom |
| `chuyen_anh` | next photo |
| `ap_dung_bo_loc` | filter applied |
| `bam_hotspot` | hotspot click |
| `luu_moodboard` | save |
| `chia_se` | share |
| `nhan_chatbot` | chat message |
| `bam_CTA` | call-to-action click |
| `gui_form` | form sent |

Class-4's `SuKien` also carries the object, the time spent and the scroll depth.

Today only three photo events exist (`xem_khong_gian`, `luu_anh`, `chon_trac_nghiem`). `/events` stores an event only when it names a published photo, so nothing else can be recorded. The trend dashboard can say which styles people like, but not which pages they read, how far they scroll, which calls to action work, or how many forms and chat messages come in. This is roadmap item 3.1.

## What Changes

- **Seven new event types,** recorded with the same consent rule as today: a consented visitor's event is stored with its details; otherwise only that day's count for the type goes up.

  | Event | Recorded when | Details |
  | :-- | :-- | :-- |
  | `xem_trang` | a visitor leaves a page | the page's route (e.g. `/uoc-tinh`), the time spent and the deepest scroll |
  | `xem_du_an` | the page left is a project page | as `xem_trang`, plus the project's slug |
  | `bam_CTA` | a link to `/lien-he`, `/uoc-tinh` or `/trac-nghiem` is clicked, anywhere on the site | the target and the page it was on |
  | `gui_form` | the contact form, the brief or the emailed estimate is sent successfully | which form |
  | `nhan_chatbot` | a chat message gets its answer | — |
  | `chia_se` | the brief's share link is copied | — |
  | `ap_dung_bo_loc` | the filters on `/khong-gian` settle on a new non-empty choice | the chosen values |
- **Privacy:**
  - Pages are recorded by route pattern, so a brief's share code in `/bo-suu-tap/xem/<mã>` is never stored. Only a project slug or a photo id is kept as the object.
  - Staff pages (routes with roles) and visits by signed-in staff are not recorded.
  - Query strings and hashes are never stored.
- **A "Hành vi trên trang" section on the trend dashboard** (`/quan-tri/xu-huong`), for the same viewers, with the selected period. It shows:
  - the most viewed pages, with their average time and scroll depth;
  - the most viewed projects;
  - CTA clicks by target and by the page they were on;
  - forms sent by kind;
  - chat messages, shares, and the most used filter values;
  - for each type, the anonymous daily totals beside the consented counts.
- **The interest score, trends, project results, the weekly report and the lead behaviour profile are unchanged.** They read photo events only; the profile is made to ignore events without a photo, so page views don't inflate a lead's "views".

**Not included,** because their only emitters are Tùng's components (`Lightbox.vue`, `HotspotImage.vue`), which this work does not touch: `phong_to_anh`, `chuyen_anh` and `bam_hotspot`. `luu_moodboard` is the existing `luu_anh` (the heart saves into the collection), so no new type is added for it.

## Capabilities

### New Capabilities
- `analytics/behaviour-events`: the seven event types, how and when each is recorded, the privacy rules for pages and staff, and the "Hành vi trên trang" section.

### Modified Capabilities
None. `analytics/trend-dashboard` keeps its requirements; the new section is specified in the new capability. `analytics/interest-score` keeps scoring only views and saves.

## Impact

- **Backend:**
  - `backend/api.py`: the `Event` model gains the types and the fields `trang`, `doi_tuong`, `gia_tri`, `thoi_gian_dung_ms` and `do_sau_cuon`; photo-less events are stored; new `GET /analytics/behaviour?days=`;
  - new `backend/pipeline/behaviour.py`;
  - `backend/pipeline/leads.py` (the profile ignores events without a photo);
  - new `backend/tests/test_behaviour_events.py`.
- **Schema:** `su_kien` gains the columns `trang`, `doi_tuong`, `thoi_gian_dung_ms` and `do_sau_cuon`, and the type check is widened.
- **Frontend (no file by Tùng):**
  - `src/api.js` (`trackEvent`);
  - new `src/lib/pageTracking.js` (route pattern, time, scroll, CTA clicks), started from `src/main.js`;
  - `ContactForm.vue`, `BriefForm.vue`, `EstimateView.vue`, `ChatWidget.vue` (script only) and `src/composables/useBrowse.js` each send their event;
  - `TrendsView.vue` gets the new section.
