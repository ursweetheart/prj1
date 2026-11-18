## 1. Schema

- [x] 1.1 In `backend/schema.sql` (idempotent):
  - `phien_truy_cap`: add `ma_thiet_bi`, `nguon`, `thiet_bi`, `bat_dau` (backfilled from `created_at`), `ket_thuc`, `ca_nhan_hoa`, and an index on `ma_thiet_bi`;
  - `su_kien`: add `loai_doi_tuong` (backfilled), `dung_thuc_ms` and `so_ket_qua`; extend the type CHECK with `tim_kiem`, `xem_goi_y_tuong_tu` and `chon_goi_y`; add an index on `(phien_id, created_at)`;
  - new tables `phien_bat_thuong`, `tk_ngay`, `tk_gia_tri_ngay`, `tk_khong_gian_ngay`, `tk_hanh_vi_ngay`, `tk_tong_ngay`, `tk_xu_huong`, `tk_nhom_thi_hieu`, `tk_nhom_chay`, `goi_y_trang_chu`, `goi_y_trang_chu_nhat_ky` and `yeu_cau_xoa_du_lieu`.

  Verify: applying it twice on Docker succeeds.

## 2. Collector (backend)

- [x] 2.1 `POST /events` takes the batch body (design 1), plus the old single body:
  - one model validates the whole batch;
  - `cach_ms` sets `created_at`;
  - session upsert with start, end, device, source and `ca_nhan_hoa`;
  - `loai_doi_tuong` set server-side;
  - `doi_tuong` on the photo path;
  - the 3 new types;
  - anonymous counts on the Asia/Ho_Chi_Minh date.

  Tests:
  - a batch of 3 is stored at the right times;
  - an invalid event gives 422 and nothing is stored;
  - the old body still works;
  - session fields are refused on a declined batch;
  - `chon_goi_y` on an unpublished space stores nothing.
- [x] 2.2 Add `POST /privacy/xoa-du-lieu` (design 3) with its rate limit and log. Tests:
  - it deletes the session and the device's sessions with their events;
  - conversations and leads survive, detached;
  - an unknown id deletes nothing;
  - the log row holds only counts.

## 3. Nightly processing

- [x] 3.1 Create `backend/pipeline/rollup.py` (design 4), covering:
  - which days to run;
  - enrichment, including project views;
  - real dwell time;
  - the 3 abnormal-session rules;
  - the daily aggregates;
  - `tk_ngay`;
  - `tk_xu_huong` using `trends.trend()`;
  - CLI `--ngay`;
  - `due_and_run()` with an advisory lock.

  Tests: dwell from the next event, capped at 30 min; each abnormal rule drops the session; a re-run replaces rather than adds; today is never processed; missed days are caught up; a project view gets its project's values; the store holds no session id.
- [x] 3.2 Create `backend/pipeline/taste_groups.py` (design 5) and call it at the end of the run. Tests:
  - two clearly separated synthetic populations give two groups with the right defining values;
  - fewer than 10 sessions records "too little data";
  - a signature seen within 28 days is not "mới", and one unseen is.
- [x] 3.3 Wire `rollup.due_and_run()` into `_weekly_once` in `api.py`: on unless `D3_NIGHTLY=off`, and never under pytest. Verify on Docker: after a restart the run happens within the first check and `tk_ngay` holds yesterday.

## 4. Readers

- [x] 4.1 Rewrite `trends.overview` on the store (design 6), keeping the response fields and adding `den_ngay` and `nhom_thi_hieu`, with new taste groups in the alerts. Update `test_trends*` to process the days first. All existing scenarios of `analytics/interest-score` and `analytics/trend-dashboard` must stay green.
- [x] 4.2 Rewrite `behaviour.overview` on `tk_hanh_vi_ngay`, adding `tim_kiem` and `goi_y` (shown, accepted, rate). Update its tests.
- [x] 4.3 Move `weekly_report._totals` and `project_stats`' views and saves onto the store. Update their tests.
- [x] 4.4 `demo_activity` generate and remove reprocess the touched days. Update its tests.

## 5. Homepage suggestions

- [x] 5.1 Backend (design 7): `GET /home/suggestions`, plus `GET` and `PUT /analytics/home-suggestions` with the log. Tests:
  - order: prioritised, then personal, then trend, then score;
  - hidden values and `khac` are never used;
  - at most 2 spaces per value, and at most 8;
  - personal ordering only for a session with `ca_nhan_hoa`;
  - roles (403 / 401).
- [x] 5.2 Create `src/components/TrendingSpaces.vue`:
  - accessible list of links with images and alt text, and the reason line;
  - hidden when the backend is off or the list is empty;
  - 360px friendly.

  Add the approved line to `HomeView.vue`.
- [x] 5.3 In `TrendsView.vue`:
  - "Số liệu đến hết ngày …", and the no-data state;
  - taste-group section with the "mới" badge;
  - search and suggestion figures in the behaviour section;
  - Tự động / Ưu tiên / Ẩn on each ranked value and alert;
  - homepage preview.

## 6. Browser

- [x] 6.1 `src/api.js`:
  - queue with a flush every 5 s and on hidden / pagehide;
  - `cach_ms`;
  - session fields;
  - `consent.analytics()` / `consent.personal()`;
  - device id lifecycle;
  - `tim_kiem` / `xem_goi_y_tuong_tu` hooks in `searchSpaces`, `searchByImage` and `getSimilar`.

  Switch the 8 `consent.get() === 'yes'` sites to `consent.analytics()`. Add vitest tests for source and device classification and batch assembly.
- [x] 6.2 `pageTracking.js`: `chon_goi_y` when a remembered similar space is opened.
- [x] 6.3 `ConsentBanner.vue`:
  - three choices and the Tùy chỉnh switches, with Cá nhân hóa tied to Phân tích;
  - reopen on `d3-consent-open`;
  - "Xóa dữ liệu của tôi" with confirmation and the result message.

  Add the "Cài đặt dữ liệu" button to `SiteFoot.vue`.

## 7. Verification

- [x] 7.1 Browser on Docker (headless), as a visitor:
  - accept, browse 3 photos, search by description, open a similar space, close the tab; check one batch arrives and the events and session fields are stored;
  - Tùy chỉnh analytics-only; footer reopen; withdraw; delete my data (counts shown, rows gone);
  - keyboard only, and at 360px.
- [x] 7.2 Run the nightly job, then open `/quan-tri/xu-huong` as sales:
  - "Số liệu đến hết ngày" shows yesterday;
  - taste groups (with demo data);
  - search and suggestion figures;
  - prioritise a value and see the homepage section change; hide one.
- [x] 7.3 Full `pytest` and `npm test` green (apart from the 4 known environment failures). Remove the test data, record the results here.

## Results (2026-11-18)

- **Backfill:** `python -m pipeline.rollup` processed 13–17/11 (108 events, 0 abnormal sessions) in about 1 s. After a restart, the scheduler reprocessed yesterday within its first check.
- **Bugs found by the tests and fixed:**
  - Postgres `LEAST()` ignores NULL, which gave a session's last event 30 minutes of dwell time instead of none;
  - `isinstance` on the batch body broke after a test reloads `api`;
  - the visit source was read lazily, after reloads had replaced the referrer;
  - the batch was flushed before the final page view was recorded.
- **Browser, headless, as a visitor:**
  - the notice offers Đồng ý / Từ chối / Tùy chỉnh;
  - one browse produced 6 requests carrying 16 events;
  - the session was stored with source `tim_kiem`, device `may_tinh` and a device id;
  - `xem_goi_y_tuong_tu`, `chon_goi_y` (with its source) and `tim_kiem/mo_ta` (17 results, words never sent) were stored;
  - the footer link reopened the notice with both switches on; analytics-only was saved; personalisation was disabled without analytics;
  - "Xóa dữ liệu của tôi" reported "Đã xóa 1 phiên, 16 sự kiện" and the rows were gone;
  - after withdrawing, only anonymous batches were sent;
  - at 360px the notice fits.
- **Browser, as a lead architect, with 240 demo sessions:**
  - the dashboard showed "Số liệu đến hết ngày 17/11/2026", two taste groups (79% and 21%, both new) and the search and suggestion figures;
  - prioritising Indochine put it first in the preview and on the homepage section, and hiding Luxury kept it off;
  - both changes were logged, then reset;
  - no horizontal scroll at 360px.
- **Tests:** `pytest` 493 passed (4 known environment failures); `npm test` 81 passed. The demo data was removed (its days reprocessed).
