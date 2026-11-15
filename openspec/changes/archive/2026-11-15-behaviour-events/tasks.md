# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Schema:** re-apply it with `docker compose exec -T db psql -U d3 -d d3 -q -v ON_ERROR_STOP=1 < backend/schema.sql`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.
- **Throw-away data:** test sessions are throw-away (`t…`) and removed. Anonymous counts are checked as differences.
- **Tùng's files stay untouched:** check with `git diff --stat` that no file by Tùng changed.

## 1. Backend

- [x] 1.1 Schema: add the `su_kien` columns `trang`, `doi_tuong`, `thoi_gian_dung_ms` and `do_sau_cuon`, and widen the type check to the 10 types.

  Verify that `schema.sql` applies twice without errors.
- [x] 1.2 `POST /events`: add the new types and validated fields; store photo-less events for consented sessions; keep the anonymous count otherwise. Make `leads.behaviour_profile` read photo events only.

  Verify with tests:
  - a consented `xem_du_an` with route, object, time and scroll is stored as sent;
  - an unconsented `bam_CTA` stores no row and raises the day's count by 1;
  - invalid route, object, filter value, time or scroll each give 422;
  - photo events still behave as before;
  - a session with 3 photo views and 5 page views gives a profile with 3 views.
- [x] 1.3 Create `backend/pipeline/behaviour.py` and `GET /analytics/behaviour?days=`, with the same roles as `/analytics/overview`.

  Verify with tests on throw-away sessions:
  - page averages: 2 views of 20 s and 40 s give 30 s, and scroll 0.5 and 1 gives 75%;
  - projects, CTA by target and page, forms by kind, chat and share counts, and top filter values match;
  - the anonymous counts show;
  - visitor 403, anonymous 401, `days=10` 422;
  - the JSON has no `phien_id`.

## 2. Frontend

- [x] 2.1 Add `trackEvent` to `src/api.js` and create `src/lib/pageTracking.js`, started in `main.js`:
  - page timing and scroll;
  - visibility pause;
  - route pattern and object;
  - the staff skip;
  - the CTA click listener.

  Wire in `gui_form` (ContactForm, BriefForm, EstimateView), `chia_se` (BriefForm copy), `nhan_chatbot` (ChatWidget script) and `ap_dung_bo_loc` (useBrowse, debounced).

  Unit-test the pure parts with vitest: route pattern, object choice, the CTA target from an href with and without the base, the scroll fraction, and the filter list and its de-duplication.

  Verify in the browser as a consenting visitor:
  - home → a project page (wait about 3 s, scroll to the end) → `/uoc-tinh` gives a `xem_trang` for `/` and a `xem_du_an` with the slug, time ≥ 3000 and scroll ≈ 1;
  - clicking the home "Liên hệ" CTA gives a `bam_CTA` for `/lien-he` from `/`;
  - sending the contact form (after 3 s) gives `gui_form` with `lien_he`;
  - a chat message gives `nhan_chatbot`;
  - choosing a style filter on `/khong-gian` gives one `ap_dung_bo_loc`;
  - opening `/bo-suu-tap/xem/<code>` stores `/bo-suu-tap/xem/:ma` and not the code;
  - a declining visitor stores no rows;
  - a signed-in architect stores nothing.

  Remove all test rows afterwards.
- [x] 2.2 Add the "Hành vi trên trang" section to `TrendsView.vue` (`getBehaviour`).

  Verify in the browser as sales, with the rows above present:
  - the figures match the API;
  - the period switch reloads them;
  - no sideways scroll at 360px.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - UC21;
  - roadmap 3.1;
  - seq-4;
  - the API table;
  - the note that the photo zoom, next photo and hotspot click events need Tùng's components.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
