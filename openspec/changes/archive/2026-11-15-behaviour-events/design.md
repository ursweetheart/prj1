# Design

## Context

- **`POST /events`** (public, 120/min) takes `{loai: xem_khong_gian | luu_anh | chon_trac_nghiem, dong_y, phien_id?, space_id?}`.
  - **Without consent:** it increments `su_kien_an_danh (ngay, loai)`.
  - **With consent:** it upserts `phien_truy_cap` and inserts `su_kien` *only* via `SELECT … FROM space WHERE id = space_id AND published`, so photo-less events would vanish. `su_kien.gia_tri` holds the photo's taxonomy values at that moment. The type CHECK lists the three types.
- **Client:** `track(loai, spaceId)` in `src/api.js` reads the banner answer (`consent.get() === 'yes'`) and `visitId()` (sessionStorage).
- **Readers of `su_kien`** filter by type (`trends`, `project_stats`, `weekly_report`, `discovery`), except `leads.behaviour_profile`, which reads every event of a session.
- **Ownership.** The Lightbox and HotspotImage are Tùng's (no edits). `main.js`, `useBrowse.js`, `ContactForm.vue`, `BriefForm.vue`, `EstimateView.vue`, `TrendsView.vue` and the chat box's script are ours.
- **Routes** carry `meta.roles` for staff pages. Project pages are `/du-an/:slug`, photos `/khong-gian/:id`, the shared brief `/bo-suu-tap/xem/:ma`.

## Goals / Non-Goals

**Goals:**
- Record the seven events with the existing consent rule.
- Store page time and scroll depth.
- Never store secrets or personal text.
- Show useful aggregates.
- Leave all existing figures unchanged.

**Non-Goals:**
- Tùng's components' events.
- Heatmaps.
- Session replay.
- Funnels across sessions.
- A nightly analytics store.

## Decisions

### 1. Schema
```sql
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS trang text;              -- route pattern, e.g. /du-an/:slug
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS doi_tuong text;          -- object: project slug, photo id, CTA target, form kind
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS thoi_gian_dung_ms int;
ALTER TABLE su_kien ADD COLUMN IF NOT EXISTS do_sau_cuon real;
-- type check widened to the 10 types
```
`gia_tri` (existing) holds the filter values of `ap_dung_bo_loc`, as `dimension:value`, which is the same format as photo events. The trend queries filter by `loai = ANY(SCORED)`, so these values never enter the score.

### 2. `POST /events`
**The `Event` model:**
- `loai` adds `xem_trang`, `xem_du_an`, `bam_CTA`, `gui_form`, `nhan_chatbot`, `chia_se` and `ap_dung_bo_loc`;
- optional fields: `trang` (`^/[a-z0-9/:_-]{0,99}$`), `doi_tuong` (`^[A-Za-z0-9_/-]{1,100}$`), `gia_tri` (≤ 20 items matching `^[a-z0-9_]+:[A-Za-z0-9_]+$`), `thoi_gian_dung_ms` (0–86,400,000) and `do_sau_cuon` (0–1).

**Storing:**
- **Photo types** keep today's insert.
- **The others** are inserted directly with `space_id` NULL.
- **Without consent,** only the daily count for the type increases, as today.

Field values are validated, never trusted. The `trang` pattern cannot hold a share code, because `:ma` is literal text in the pattern.

### 3. Client (`src/lib/pageTracking.js`, started in `main.js`)
- **`trackEvent(loai, fields)`** in `src/api.js`, the same consent logic as `track()`. It uses `keepalive: true`, so a page-leave event survives the tab closing.
- **Skip rule:** skip when `session.user` exists and its role is not `visitor`, or when the route has `meta.roles`.
- **Page timing:**
  - `router.afterEach(to, from)`: when the path changed, close the previous page (send `xem_trang` / `xem_du_an` with the elapsed time and the deepest scroll) and open the new one.
  - **Deepest scroll** comes from a passive `scroll` listener: `(scrollY + innerHeight) / scrollHeight`, capped at 1.
  - **`visibilitychange` to hidden** closes the page; becoming visible opens it again, so background time isn't counted.
- **Pattern:** `to.matched.at(-1).path` (e.g. `/du-an/:slug`). The object is `to.params.slug` for `/du-an/:slug`, `to.params.id` for `/khong-gian/:id`, and nothing otherwise.
- **CTA:** one capture-phase `click` listener on `document`. For `a[href]` whose path (minus the base `/prj1`) is `/lien-he`, `/uoc-tinh` or `/trac-nghiem`, send `bam_CTA` with `doi_tuong` = the target and `trang` = the current route pattern. This covers Tùng's home CTA, the nav, the footer and our pages without editing them.
- **Components:**
  - `ContactForm` sends `gui_form` with `lien_he`, `BriefForm` with `brief` and `EstimateView` with `uoc_tinh`, each after a successful response;
  - `BriefForm`'s copy link sends `chia_se` with `brief`;
  - `ChatWidget` sends `nhan_chatbot` after an answer;
  - `useBrowse` debounces 1.5 s after the selection changes; if it is non-empty and differs from the last one sent, it sends `ap_dung_bo_loc` with the `dim:value` list.

### 4. `pipeline/behaviour.py` and `GET /analytics/behaviour?days=7|30|90`
Same viewers as `/analytics/overview` (`sales` and approvers). It returns:
- `trang`: top 10 page patterns with count, average seconds and average scroll percentage;
- `du_an`: top 10 projects by `xem_du_an`;
- `cta`: counts by target, and by page within the target;
- `form`: counts by kind;
- `chat` and `chia_se`: counts;
- `bo_loc`: the top 10 filter values;
- `an_danh`: the anonymous counts per new type for the period;
- `co_du_lieu_mo_phong`, as the overview has.

Demo sessions are included and labelled by the existing banner.

### 5. Dashboard
`TrendsView.vue` adds a "Hành vi trên trang" card section, loaded with the same period switch:
- a page table that becomes stacked rows under 600px;
- lists for projects, CTAs (target → pages), forms and filter values;
- small numbers for chat and shares;
- a line on each list giving the anonymous total.

### 6. Lead profile
`behaviour_profile` keeps only events with `space_id IS NOT NULL`, which is exactly what it reads today, so page events cannot change a lead's view count.

## Risks / Trade-offs

- **[`keepalive` requests can be dropped]** → Some page-leave events are lost. They are counts, so this is accepted.
- **[A client can send made-up events]** → This was already true of `/events`. Everything is validated, rate-limited and counts-only.
- **[Pattern instead of real path loses which shared brief was read]** → That's intended: it's private.
- **[Staff skip relies on the signed-in role]** → Staff browsing while signed out is counted, as a visitor.

## Migration Plan

- Apply `schema.sql` (it can be re-run) and rebuild the backend and web.
- **Rollback:** the old client sends only the old types, and the new columns are nullable.
