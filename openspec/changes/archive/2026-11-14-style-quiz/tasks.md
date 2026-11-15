# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container on a copy of the sources.
- **Browser checks** use the scratchpad Playwright pattern at 1280px and 360px.

## 1. Data and events

- [x] 1.1 Make these idempotent changes in `backend/schema.sql`, then re-apply it:
  - widen `su_kien_loai_check` to `('xem_khong_gian', 'luu_anh', 'chon_trac_nghiem')`;
  - add the table `ket_qua_trac_nghiem` (design decision 6).

  Also add `chon_trac_nghiem` to the `Event` Literal in `backend/api.py`.

  Verify with tests in a new `tests/test_quiz.py`:
  - a consented `chon_trac_nghiem` is stored with the taxonomy snapshot;
  - a non-consented one bumps `su_kien_an_danh`;
  - `tests/test_events.py` still passes.
- [x] 1.2 In `pipeline/trends.py`, limit both `su_kien` reads in `overview()` to `xem_khong_gian` and `luu_anh`.

  Verify with a test in `tests/test_trends.py`:
  - quiz events on a value leave its score, views, saves and trend unchanged;
  - no KeyError;
  - the existing trend tests still pass.

## 2. Quiz logic

- [x] 2.1 Create `backend/pipeline/quiz.py` with `build_pairs(spaces, rnd, n=6)` (design decision 2). It works on plain tuples, so it is a pure function.

  Verify with unit tests:
  - 4 styles × 3+ photos give 6 pairs, 12 distinct photos and 3 per style;
  - every pair has two different styles;
  - pairs share a space type when both styles have one;
  - Indochine 13 + Japandi 3 gives fewer than 4 pairs;
  - a 1-photo style and `Khac` never appear;
  - two seeds give different pairs.
- [x] 2.2 Add `score(shown_styles, chosen_styles)` and the answer validation (design decisions 1 and 3) to `pipeline/quiz.py`.

  Verify with unit tests:
  - the spec example gives Japandi 50% and Hiện đại 33%;
  - one chosen style gives that style alone at 100%;
  - each of these is rejected: a chosen id not in any pair, two picks from one pair, duplicate photos across pairs, fewer than 2 picks, more than 6 pairs.
- [x] 2.3 Add `suggest(conn, chosen, shown, styles, k=8)`, which uses the embedding centroid query from design decision 4.

  Verify with a DB test:
  - the results are published, belong to the top styles and exclude the shown photos;
  - the first result is the closest to the average of the chosen embeddings;
  - an unpublished space never appears.

## 3. Endpoints

- [x] 3.1 Add `GET /quiz` and `POST /quiz/result` (no auth). `GET /quiz` answers 409 `chua_du_anh` when fewer than 4 pairs can be made. `POST /quiz/result` returns `{phong_cach, goi_y}`, with names from the taxonomy.

  Verify with API tests:
  - `GET /quiz` returns only published photos;
  - a full round trip gives a result;
  - a forged pick gives 422;
  - an unpublished id gives 422;
  - 409 when the published pool is reduced to one style (inside a transaction or with throwaway spaces, so real data is untouched).
- [x] 3.2 Add `GET /quiz/me` and `PUT /quiz/me` (signed in, `SIGNED_IN` limiter). PUT re-scores and upserts the result.

  Verify with API tests:
  - anonymous calls get 401;
  - PUT then GET returns the result;
  - a second PUT replaces it;
  - another account cannot see it;
  - a suggestion that is later unpublished is dropped on GET.

## 4. Frontend

- [x] 4.1 In `src/api.js`, add `getQuiz`, `postQuizResult`, `getMyQuiz`, `saveMyQuiz` and `trackQuizPick`. Create `src/lib/quiz.js` for the browser copy of the last result and `pendingSave`, which is sent to `PUT /quiz/me` once on sign-in.

  Verify with `src/lib/quiz.test.js`:
  - storing and loading the last result works, and a storage error is tolerated;
  - `pendingSave` sends once after sign-in and is then cleared;
  - `trackQuizPick` is skipped for staff.

  Vitest passes.
- [x] 4.2 Create `src/views/QuizView.vue` at `/trac-nghiem` with the start, question and result states. Design decision 7 covers keys, alt text, back and skip, "Lưu tất cả", "Lưu kết quả", "Làm lại", and the offline and `chua_du_anh` messages. Add the route.

  Verify in the browser:
  - a full attempt shows "Câu i/n" and ends on a result with 2 styles and up to 8 tiles;
  - back changes an answer;
  - skipping everything shows the "chọn ít nhất 2 ảnh" message;
  - the hearts and "Lưu tất cả" update the header count;
  - a reload shows the last result;
  - no horizontal scroll at 360px;
  - keyboard only (Tab, 1, 2, Esc) works.
- [x] 4.3 Link the result to `/khong-gian#phong_cach=X`, which `useBrowse` already reads as the selected style filter. Add the quiz links to `SpaceSearchBand.vue`, `SpacesView.vue` and `SiteFoot.vue`.

  Verify in the browser:
  - "Xem thêm phong cách Japandi" opens `/khong-gian` with Japandi selected and only Japandi results;
  - each of the 3 links opens `/trac-nghiem`.
- [x] 4.4 Check the sign-in-to-save flow end to end.

  Verify in the browser:
  - an anonymous visitor presses "Lưu kết quả", signs in with a visitor test account and lands back on `/trac-nghiem`, which shows "Đã lưu kết quả";
  - a fresh browser context signed in to the same account shows the saved result;
  - with consent, each pick created one `chon_trac_nghiem` row and skips created none.

## 5. Docs

- [x] 5.1 Update `TONG-QUAN-DU-AN.md`: mark UC06 and seq-12 as done, update roadmap 2.5, and add the quiz endpoints to the API table, the new table and event type, and the page `/trac-nghiem`. Verify that `/openapi.json` lists the 4 `/quiz` endpoints and that the full backend suite shows no new failures beyond the 8 known ones.
