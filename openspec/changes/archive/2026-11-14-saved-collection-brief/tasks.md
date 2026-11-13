# Tasks

Backend tests run in the stack: `docker compose up -d --build backend` then `docker compose exec backend python -m pytest tests/<file> -q`. Frontend builds through `docker compose build web`, because the local `node_modules` was installed on Windows. Browser checks use the Playwright script pattern from lead-intake (scratchpad), at 1280px and 360px.

## 1. Data model

- [x] 1.1 Append the idempotent collection block to `backend/schema.sql`: tables `bo_suu_tap` (with the `loai` CHECK and `ma_chia_se` UNIQUE) and `bo_suu_tap_anh` (PK and cascades), the partial unique index for one `dang_luu` collection per user, and `lead.bo_suu_tap_id` (ON DELETE SET NULL). Verify that applying `schema.sql` twice to the running DB gives no error and `\d bo_suu_tap`, `\d bo_suu_tap_anh`, `\d lead` show the columns and constraints.

## 2. Collections API

- [x] 2.1 Add the `ids` filter to `GET /spaces` (comma list, ≤ 60, published-only for visitors). Verify with a test in `tests/test_collections.py`: `?ids=` with one draft and two published ids returns only the two published ones to a visitor, and more than 60 ids gives 422.
- [x] 2.2 Add `GET /collections/me`, `PUT/DELETE /collections/me/items/{space_id}` and `POST /collections/me/merge` (signed-in, `limit("collections", 120, 60)`), creating the user's `dang_luu` row on first use. Verify with tests: add, note update, remove; a draft space gives 404; the 61st gives 409 `bo_suu_tap_day`; anonymous gives 401; merge adds missing items, fills an empty account note from the browser note and keeps a non-empty one, and caps at 60; a space unpublished later is not returned.

## 3. Brief

- [x] 3.1 Add `brief_summary(space_ids)` to `backend/pipeline/leads.py` (leading style with share, leading tone, up to 2 space types on ≥ 2 photos, `*:khac` ignored, `line`), and a `bo_suu_tap_id` parameter to `create_lead`. Verify with tests: the spec's 5-photo case gives "Wabi-sabi 60% · tông Ấm · phòng khách", a single photo gives its own space type, and `khac` never appears.
- [x] 3.2 Add `BriefIn(LeadIn)` and `POST /briefs` (shared `limit("leads", 5, 600)`): the frozen `da_gui` copy with `ma_chia_se` and `tom_tat`, then `create_lead("brief", request={loai_nha, dien_tich_m2, ngan_sach, tom_tat}, bo_suu_tap_id=…)`, then both notices in background tasks. Add `GET /collections/shared/{ma}`. Verify with tests: an anonymous brief creates the lead and copy, and the shared view has photos, notes and summary but no name or phone; editing the account collection afterwards leaves the shared view unchanged; no published space gives 422 and no rows; honeypot or a fast send gives 201 with nulls and no rows; a 6th lead-or-brief in 10 minutes gives 429; an unknown code gives 404; the profile follows the double-consent rule.
- [x] 3.3 Extend `notify.py` for briefs: house type, area and budget labels, summary line and share URL in the sales email; the share URL in the visitor confirmation; log lines without contact data. Verify with tests using the existing `FakeSMTP`: the sales body contains "Bộ sưu tập (brief)", the house type label, the summary and `/bo-suu-tap/xem/<ma>`; the visitor body contains the link and no profile.
- [x] 3.4 Have `GET /leads` return `bo_suu_tap_id`, the brief's share code and its items (space fields plus note), and accept `nguon=brief`. Verify with a test: a brief lead lists its items and code, and `?nguon=brief` returns only briefs.

## 4. Frontend: saving

- [x] 4.1 Create `src/lib/collection.js`: a reactive store with browser mode (`localStorage['d3_bo_suu_tap']`, try/catch, memory fallback) and account mode, switching on `session.user` with merge-then-clear. Add the collection calls and `getSpacesByIds` to `src/api.js`. Verify with `src/lib/collection.test.js` (vitest, run in the web build stage or with `npx vitest` in the container): toggle, note, the cap at 60, and that the merge is called once on sign-in with the browser items and that the key is then cleared.
- [x] 4.2 Create `SaveHeart.vue` and place it on `SpaceTile.vue` (wrapper div; the link is unchanged) and in the `SpaceView.vue` title row. Verify in the browser: the heart toggles without opening the tile, `aria-pressed` follows the state, the tile still opens the space page, the full-collection message shows at 60, and `/khong-gian` at 360px has no horizontal scroll.
- [x] 4.3 Add the "Bộ sưu tập" header link with its count to `SiteNav.vue` (only when `ai.state === 'on'`). Verify in the browser that it shows "Bộ sưu tập (4)" after 4 saves, is absent when the backend is stopped, and that the signed-out header at 360px has no horizontal scroll.

## 5. Frontend: collection page and brief

- [x] 5.1 Create `CollectionView.vue` with routes `/bo-suu-tap` and `/bo-suu-tap/xem/:ma`: the grid, a note per photo saved on blur, remove, the empty state with a link to `/khong-gian`, the sign-up invitation when anonymous, the read-only shared view, and "Không tìm thấy bộ sưu tập". Verify in the browser: the anonymous and empty scenarios of `collections/saved-collection`, a note surviving a reload, and the shared view with no contact data.
- [x] 5.2 Create `BriefForm.vue` (fields, notice, "N ảnh … sẽ được gửi kèm", validation, opt-in box, 422/429 handling, confirmation with share link and copy). Verify in the browser: wrong phone shows an error under the field with nothing sent; a valid anonymous brief shows the confirmation and link; and the lead appears in `/khach-hang` with source `brief`.
- [x] 5.3 Check sign-in end to end: as an anonymous visitor, save 3 spaces with a note, register, and confirm the account collection has the 3 with the note and the browser key is gone; sign in on a fresh browser context and confirm the same 3 are there. Verify in the browser that both checks pass.
- [x] 5.4 Add the brief block and a "Bộ sưu tập" filter chip to `LeadsView.vue`. Verify in the browser as a sales user: the brief lead shows house type, area, budget, summary, photos with notes and the share link; the filter works; and there is no horizontal scroll at 360px.

## 6. Docs and integration

- [x] 6.1 Update `TONG-QUAN-DU-AN.md`: UC07/UC08 status, roadmap 2.1 and 2.2, the API table (collections, briefs, `?ids=`), the data tables (`bo_suu_tap`, `bo_suu_tap_anh`), and a note to Tùng that `SpaceTile` and `SpaceView` carry the heart. Verify that the documented endpoints match `GET /docs` on the running backend.
- [x] 6.2 Run the integration check: the full backend suite (only the known environment failures allowed), the lead-intake Playwright script (still 30/30), and the new browser checks from groups 4–5. Verify that all pass and record the results in this task. Result: backend 129 passed and 8 failed, all known (the 7 environment failures from lead-intake plus `test_project_spaces`, which hits the mixed-case `Indochine` folder in local data). The lead-intake browser script passes 30/30, the new collection script 31/31 (hearts, 60 cap, header without backend, 360px, empty/anonymous pages, notes, brief errors and confirmation, shared view without contact data, sign-up merge, second device, `/khach-hang` brief block and filter). Vitest: 32/32. Fixed along the way: a failed add was not rolled back (reactive proxy vs raw object), an empty collection stayed on "Đang tải…", and the `Khac` style code was not excluded from summaries (also in the lead-intake profile).

## Workflow follow-up

- Archive with `openspec-archive-change` after review.
- Later changes: a "saved a photo" behaviour event for trends (phase 3), and hearts in the project photo viewer once project photos are ingested as spaces.
