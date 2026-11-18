# Tasks

## 1. Ranking

- [x] 1.1 Create `backend/pipeline/project_results.py` with `rank(photos, req, k=3, per=2)` (design decision 1). Verify with `backend/tests/test_project_results.py` (no DB, no AI, taxonomy monkeypatched), one test per spec scenario: five photos from two projects → two cards; project A (Japandi + phòng khách + chung cư) ranks above B (Japandi bedroom villa with higher similarity) and its `khop` names all three; no constraints → by similarity, empty `khop`; ≤ 2 photos per card, best-matching first; ≤ 3 projects.

## 2. Assistant answers

- [x] 2.1 Add `candidates(text, limit=60)` (published only, `sim`, `loai_cong_trinh` codes; design decision 2) and use `rank` in the knowledge-base path of `respond` instead of `by_text(..., 3)`. Verify with an API test on `POST /chat`: an answer with constraints returns `projects` (≤ 3, unique folders, published photos only) and `images` equal to their photos; a draft best match never appears.
- [x] 2.2 Group the photo-answer path's used photos by project in first-use order (design decision 3). Verify with a test that stubs `answer_from_photos` to use two photos of one project: one card with both photos.
- [x] 2.3 Return `projects: []` on small talk, handoff and forbidden-topic answers. Verify that `tests/test_topic_guard.py` and the small-talk tests still pass.

## 3. Chat widget

- [ ] 3.1 Render project cards in `src/components/ChatWidget.vue` (design decision 5) and keep the thumbnails for any answer that has `images` but no `projects`. Verify with a production build, and on Docker: ask "phòng khách chung cư phong cách Japandi", see up to 3 cards with names and matched lines; a card for a project with a page opens `/du-an/<slug>?anh=…` on that photo, and one without opens `/khong-gian/<id>`; keyboard Tab reaches each card and Enter opens it.

## 4. Integration and docs

- [x] 4.1 Run the full `pytest` suite and `npm test`; only the already-known failures may remain. On Docker, ask a follow-up ("cho mình xem phòng ngủ") after giving a style earlier, and check the earlier style still ranks the projects.
- [x] 4.2 Update `TONG-QUAN-DU-AN.md`: M4 / assistant row (example projects ranked by matched constraints) and the 11.2 `/chat` response note. Verify by reading the changed rows.

## Workflow follow-up

- Archive with `openspec-archive-change` after review.
