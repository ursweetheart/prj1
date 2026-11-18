# Design

## Context

The diagrams being matched are seq-4, act-3, act-7, dfd-2-1, dfd-2-5, seq-2, seq-18 and class-4 (PhienTruyCap, SuKien). Current state:

- **`POST /events` (`api.py`):**
  - takes one event per request;
  - stores consented events in `su_kien`, with a `dimension:value` snapshot for photo events;
  - counts declined ones per day in `su_kien_an_danh`.
- **Browser:** `src/api.js` `track()` / `trackEvent()` send each event immediately (keepalive). `pageTracking.js` sends page views with dwell and scroll.
- **Reads:**
  - `pipeline/trends.py` `overview()` computes scores, trends and totals live from `su_kien`, `bo_suu_tap` and `lead`;
  - `pipeline/behaviour.py` `overview()` reads `su_kien` live;
  - `pipeline/weekly_report.py` `_totals()` reads raw tables and calls `trends.overview(conn, 7)`.
- **Scheduling:** a background loop in `api.py` (`_weekly_loop`, every 10 min) sends the weekly report and purges old conversations. It is disabled under pytest.
- **Consent:** localStorage `d3_dong_y` is `'yes'` or `'no'` (`consent.get()`), checked in 8 places.
- **Out of bounds:** `SpaceView.vue`, `SpacesView.vue` and `HomeView.vue` are Tùng's. The user approved one line in `HomeView.vue`. `SiteFoot.vue` is shared (mostly ours).
- **Tooling:** scikit-learn is already in `backend/requirements.txt`.

## Goals / Non-Goals

**Goals:** every box and arrow of the listed diagrams has a working counterpart, privacy rules are unchanged or stricter, and existing figures keep their meaning (same weights and thresholds).

**Non-Goals:**
- A separate data warehouse: the store is plain Postgres tables in the same database, which is what D10 needs at this size.
- Real-time dashboards.
- Deleting data for signed-in accounts (account deletion is an admin matter, UC24).
- Changing lead behaviour profiles.

## Decisions

### 1. Batch protocol with backward compatibility

`POST /events` accepts either:
- the old single-event body; or
- a batch `{dong_y, phien_id?, ma_thiet_bi?, nguon?, thiet_bi?, ca_nhan_hoa?, su_kien: [≤50 events]}`.

Each event has the old fields plus `cach_ms` (0–600000), and `so_ket_qua` for searches. One Pydantic model validates the whole batch, so a single bad event gives 422 for the whole request, which is what seq-4 step 4 means by "validate".

- **Declined batch:** each event type is counted in `su_kien_an_danh`; the session fields are not allowed in that case.
- **Consented batch:**
  1. Upsert `phien_truy_cap` with `bat_dau = least(...)`, `ket_thuc = greatest(...)` and the device, source and device-type fields.
  2. Insert each event with `created_at = now() - cach_ms`.
  3. Set `loai_doi_tuong` server-side from the event type.

`xem_goi_y_tuong_tu` and `chon_goi_y` join the photo-event path, so they need a published space and get its snapshot. `doi_tuong` is now stored on that path too, holding the source space id. `tim_kiem` stores `doi_tuong` (`anh` / `mo_ta`) and `so_ket_qua`.

The rate limit stays at 120 requests per 60 s. Batches make that looser per event, so the batch size caps abuse.

*Alternative:* `navigator.sendBeacon`. Rejected: its JSON body is not CORS-safelisted when the API is on another origin. `fetch` with `keepalive` already works here.

### 2. Browser collector (`src/api.js`)

- A module-level queue holds events. `setInterval(flush, 5000)` runs while the queue is non-empty, and `visibilitychange → hidden` and `pagehide` trigger a flush.
- `track()` and `trackEvent()` push to the queue instead of fetching. The consent state is read at flush time, so a choice changed in the meantime applies to the next send.
- Device id: localStorage `d3_thiet_bi`, created only while analytics consent is on, and deleted when it is turned off.
- Source: from `utm_source`, otherwise from the `document.referrer` host compared with lists of search and social hosts, computed once per tab session.
- Device type: `matchMedia('(pointer:coarse)')` plus the screen width (< 768 phone, < 1100 tablet).

### 3. Consent (`ConsentBanner.vue`)

- Stored values: `'yes'` (analytics and personalisation), `'phan_tich'` (analytics only), `'no'`.
- New helpers in `src/api.js`:
  - `consent.analytics()` returns true for `'yes'` or `'phan_tich'`;
  - `consent.personal()` returns true for `'yes'` only.

  All 8 `consent.get() === 'yes'` call sites switch to `consent.analytics()`.
- Tùy chỉnh shows two switches (`role="switch"`, `aria-checked`), with Cá nhân hóa disabled while Phân tích is off.
- The footer link dispatches `window` event `d3-consent-open`, and the banner listens and reopens.
- "Xóa dữ liệu của tôi" sits in the reopened panel and needs a confirm step. It calls `POST /privacy/xoa-du-lieu {phien_id, ma_thiet_bi}`, rate-limited to 5 per 60 s.
  - The server deletes `phien_truy_cap WHERE id = %s OR ma_thiet_bi = %s`. `su_kien` and `phien_bat_thuong` cascade; `hoi_thoai.phien_id` and `lead.phien_id` are already `ON DELETE SET NULL`.
  - It logs `yeu_cau_xoa_du_lieu(luc, so_phien, so_su_kien)` and returns the counts.
  - The browser then drops its session id and device id.

### 4. Nightly processing (`pipeline/rollup.py`)

- **Days:** Asia/Ho_Chi_Minh dates, `(created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date`. Anonymous counts are inserted with the same expression instead of `current_date`, so both sides agree.
- **Which days to run:** `run(conn, days=None)` processes every date from the earliest raw row (events, briefs, leads or anonymous counts; at most 400 days back) to yesterday that is missing from `tk_ngay`. With `days` given, it reprocesses exactly those dates.
- **Per day, in one transaction:**
  1. **Enrich:** `UPDATE su_kien SET gia_tri = <space values>` where `gia_tri = '{}'` and `space_id` is set. `xem_du_an` events get the union of values of `space` rows with `du_an_slug = doi_tuong` and status published.
  2. **Real dwell:** `dung_thuc_ms = least(coalesce(thoi_gian_dung_ms, lead(created_at) over (partition by phien_id order by created_at) - created_at), 30 min)`.
  3. **Abnormal sessions:** the three rules (more than 500 events in the day; ≥ 60 in one minute, using `date_trunc('minute')` buckets; ≥ 20 views all under 1 s) write `phien_bat_thuong(ngay, phien_id, ly_do)`.
  4. **Aggregate:** delete then insert the day's rows in:
     - `tk_gia_tri_ngay(ngay, gia_tri, so_xem, so_luu, so_brief, so_phien, tong_dung_ms)`;
     - `tk_khong_gian_ngay(ngay, space_id, so_xem, so_luu)`;
     - `tk_hanh_vi_ngay(ngay, loai, trang, doi_tuong, so_luot, tong_dung_ms, so_co_dung, tong_cuon, so_co_cuon)`: filter values are exploded with one row per value (`doi_tuong` = value), and searches use `doi_tuong` = kind;
     - `tk_tong_ngay(ngay, so_brief, lead jsonb)`.

     Only consented events from sessions not marked abnormal for that day are counted.
  5. Upsert `tk_ngay(ngay, xu_ly_luc, so_su_kien, so_phien, so_phien_bat_thuong)`.
- **After the days:** for the last processed day `D`:
  - compute weekly scores from `tk_gia_tri_ngay`: week 0 = D-6..D, weeks 1–4 before it;
  - apply the existing `trends.trend()`;
  - store `tk_xu_huong(ngay_tinh, gia_tri, tuan0, tb4, so_tin_hieu, thay_doi, xu_huong)`;
  - run the taste groups.
- **Scheduling:** `api.py`'s maintenance check (already every 10 min) also calls `rollup.due_and_run()`. That runs when the local time is ≥ 01:00 and yesterday is not in `tk_ngay`, taking `pg_try_advisory_lock` so two processes never run it together. It is off under pytest like the weekly loop, and `D3_NIGHTLY=off` disables it.
- **Manual run:** `python -m pipeline.rollup [--ngay 2026-11-10 ...]`.

### 5. Taste groups (`pipeline/taste_groups.py`)

- **Input:** for each session with ≥ 3 enriched events in the 30 days up to D (consented, non-abnormal, non-`khac` values), a count vector over `dimension:value`.
- **Vectors:** log(1 + count) weighting, then L2 normalisation.
- **Clustering:** scikit-learn `KMeans(n_init=10, random_state=0)` for k = 2..min(6, n−1). The k with the best `silhouette_score` wins. With fewer than 10 sessions there is no run, and `tk_nhom_chay(ngay_tinh, so_phien, du_lieu = false)` records that.
- **Defining values:** lift = (share of the group's sessions with the value) / (share of all sessions with it). The top 3 with lift > 1 that occur in ≥ 20% of the group are kept.
- **New:** the sorted top-2 signature is absent from the `tk_nhom_thi_hieu` rows of the previous 28 run dates.
- **Storage:** `tk_nhom_thi_hieu(ngay_tinh, nhom, so_phien, ty_le, gia_tri text[], moi)`. New groups are returned by the overview's alerts with kind `nhom_moi`.

### 6. Readers on the store

- `trends.overview(conn, days)` reads `tk_*`: the period is `[D-days+1, D]` where D = `max(tk_ngay.ngay)`. Scores sum `tk_gia_tri_ngay`, trends and alerts come from `tk_xu_huong` at D, totals and leads come from `tk_tong_ngay` plus `su_kien_an_danh`, and top spaces come from `tk_khong_gian_ngay`. It adds `den_ngay` and `nhom_thi_hieu`; with no `tk_ngay` row it returns `den_ngay: null`.
- `behaviour.overview` reads `tk_hanh_vi_ngay`, and adds searches by kind and suggestions shown / accepted.
- `weekly_report._totals` reads the same tables.
- `project_stats` (seq-18 step 11 "hiệu quả từng dự án") takes views and saves from `tk_khong_gian_ngay`. Leads and briefs per project stay on their own tables, which are records rather than events.
- Response field names stay the same, so `TrendsView` only gains the new sections.

### 7. Homepage suggestions

- **Storage:** `goi_y_trang_chu(gia_tri PK, che_do 'uu_tien'|'an', nguoi_id, luc)` and the log `goi_y_trang_chu_nhat_ky`.
- **`GET /home/suggestions?phien_id=`** (public, rate-limited):
  1. Order values as: prioritised; then the session's top values, only if that session exists with `ca_nhan_hoa = true`; then `tk_xu_huong` rising / new at D; then 30-day score.
  2. Drop hidden values, `khac` and dimensions not shown to visitors.
  3. Take up to 2 published spaces per value from `space_gia_tri`, ordered by 30-day views in `tk_khong_gian_ngay`, skipping spaces the session already viewed and spaces already chosen, until there are 8.
  4. Return `[{id, relative_path, alt_text, ly_do: {chieu, ten, nguon: uu_tien|ca_nhan|xu_huong|diem}}]`.
- **Staff endpoints:** `GET /analytics/home-suggestions` returns the settings and a preview; `PUT /analytics/home-suggestions` sets `{gia_tri, che_do}`. Roles: sales plus approvers, like the dashboard.
- **Session flag:** the batch sends `ca_nhan_hoa`, stored on `phien_truy_cap`. A session id sent without it is ignored, so a visitor who allowed analytics only gets the common list.
- **Frontend:** `src/components/TrendingSpaces.vue` shows the list when `aiAvailable()` succeeds and the list is non-empty. It sends `phien_id` only when `consent.personal()`. `HomeView.vue` gets one line, between ProjectGrid and SpaceSearchBand.

### 8. Search and similar events without touching Tùng's views

In `src/api.js`:
- `searchSpaces` (only when `q` is non-empty) and `searchByImage` queue `tim_kiem` after a successful response.
- `getSimilar(id)` queues `xem_goi_y_tuong_tu` and remembers `{src: id, ids}`.

`pageTracking.js`, which already watches route changes, queues `chon_goi_y` when the new route is `/khong-gian/:id` with an id in the remembered set. The memory is cleared after use.

### 9. Schema (`schema.sql`, idempotent)

- `phien_truy_cap`: add `ma_thiet_bi`, `nguon`, `thiet_bi`, `bat_dau` (backfilled from `created_at`), `ket_thuc` and `ca_nhan_hoa`, with an index on `ma_thiet_bi`. `da_dong_y_thu_thap` stays true for every row.
- `su_kien`:
  - add `loai_doi_tuong`, `dung_thuc_ms` and `so_ket_qua`;
  - extend the type CHECK with the 3 new types;
  - backfill `loai_doi_tuong`;
  - add an index on `(phien_id, created_at)`.
- New tables: `phien_bat_thuong`, the `tk_*` tables, `goi_y_trang_chu` with its log, and `yeu_cau_xoa_du_lieu`.

## Risks / Trade-offs

- **[Dashboard lags a day]** This is what seq-4 draws. The dashboard states the date, and demo generation and an operator can reprocess at once.
- **[Snapshot vs. enrichment]** Values captured at event time stay, as class-4's note demands. Enrichment only fills gaps, and project views were never scored, so scores keep their meaning.
- **[Clustering on little data]** At least 10 sessions are needed and silhouette chooses k. With demo data the groups are labelled as demo by the existing banner.
- **[Device id is a tracking id]** It exists only under analytics consent, is never sent without it, and is used only to delete or group one browser's own sessions.
- **[Deletion by bearer ids]** Ids are 128-bit random and the endpoint is rate-limited, so a guess cannot hit.

## Migration Plan

1. Apply `schema.sql`, then run `python -m pipeline.rollup` once to backfill every past day. Rebuild the backend image.
2. Frontend: the old `'yes'` / `'no'` consent values keep their meaning, and the new `'phan_tich'` is additive.
3. **Rollback:** revert the code. The new columns and tables are ignored by the old code, and the old readers still work from the raw tables.
