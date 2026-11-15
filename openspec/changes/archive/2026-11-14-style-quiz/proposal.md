# Proposal

## Why

Many visitors come to an interior studio without words for what they like. They cannot type "Japandi" into the search or tick it in the filter, because they don't know the name. UC06 "Làm trắc nghiệm phong cách" (seq-12, usecase-1) is designed for them. They pick the photo they like better from a few pairs, the site names the styles that fit, and it shows matching published work. It is the last customer-facing use case in the diagrams that is still "Chưa" (TONG-QUAN-DU-AN.md §5, roadmap 2.5). The data it needs is already in the database: published spaces have a `phong_cach` tag and a SigLIP2 embedding.

## What Changes

- **A style quiz at `/trac-nghiem`.** The visitor answers 6 questions, and each question is a pair of published photos in two different styles, of the same kind of room where possible. The visitor taps the one they like better, and can skip a pair.
- **The server builds the pairs** from published spaces whose style is a real value (not `Khac`). It uses only styles with enough photos and balances how often each style is shown. The pairs are random on each attempt.
- **The server scores the answers**. The client sends the photos shown and the ones chosen, never scores. Each chosen photo adds a point to its style, divided by how often that style was shown. The top 2 styles are the result, with a percentage for each.
- **Suggestions use SigLIP2.** The suggested spaces are published spaces of the top styles. They are ranked by how close their image embedding is to the average embedding of the photos the visitor chose, and photos already shown in the quiz are left out. The visitor can save each one with the existing heart, or add them all to Bộ sưu tập at once.
- **Answers are behaviour signals under the existing consent rule.** Each answer sends a `chon_trac_nghiem` event for the chosen photo. It is stored with the taxonomy snapshot for a consented session, and only counted in the day's anonymous total otherwise. The interest score and trend dashboard do **not** count these events in this change: a forced choice between two photos is not the same signal as freely viewing or saving one.
- **Save the result (seq-12 opt step 16).** A signed-in visitor can save their latest result to their account. A visitor who is not signed in is asked to sign in, and the pending result is saved right after they sign in. On a later visit to `/trac-nghiem`, the saved result is shown with a "Làm lại" button. Everyone keeps their last result in the browser.
- **Entry points:** a link on the home search band, on `/khong-gian` and in the footer. The staff header already overflows, so there is no new nav item.

## Capabilities

### New Capabilities
- `style-quiz`: building the photo pairs, scoring the answers, the result and its suggestions, quiz answer events, and saving the result to an account.

### Modified Capabilities
- `analytics/interest-score`: the interest score requirement now says explicitly that only `xem_khong_gian` and `luu_anh` events (plus sent brief photos) are counted, so the new `chon_trac_nghiem` events are stored but not scored.

## Impact

- **Backend:**
  - `backend/schema.sql`: `su_kien.loai` allows `chon_trac_nghiem`, and a new table `ket_qua_trac_nghiem` holds one row per account.
  - `backend/api.py`: new endpoints `GET /quiz`, `POST /quiz/result`, `GET /quiz/me` and `PUT /quiz/me`. `/events` accepts the new type.
  - New `backend/pipeline/quiz.py`.
  - `backend/pipeline/trends.py`: filters events by type.
  - New `backend/tests/test_quiz.py`.
- **Frontend:**
  - `src/api.js`: quiz calls and `trackQuizPick`.
  - New `src/lib/quiz.js`: the result in browser storage, and saving after sign-in.
  - New `src/views/QuizView.vue`.
  - `src/router/index.js`.
  - Links in `SpaceSearchBand.vue`, `SpacesView.vue` and `SiteFoot.vue`.
- **Data limits today:** 40 published spaces in 4 styles (Indochine 13, Luxury 13, Hiện đại 8, Japandi 6). Six pairs need 12 distinct photos, which is enough. A style with fewer than 2 published photos is left out until more are published.
- **Out of scope:**
  - Suggesting **projects** rather than spaces. seq-12 step 12 says "dự án", but the project → space link has no matches until `ingest_projects.py` runs over the site photos. The result can link to `/khong-gian?phong_cach=…` instead.
  - Quiz questions on other dimensions (colour tone, material).
  - Adding the quiz result to leads and briefs.
  - Counting quiz picks in the interest score.
