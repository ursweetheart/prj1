## Why

A visitor who likes a photo (a Pinterest pin, a friend's apartment) has no words for its style, so the text search box does not help them. The library already holds a SigLIP2 image embedding for every space and `search.py` already ranks by cosine distance, so "upload a photo, see our projects that look like it" costs one endpoint and one button.

## What Changes

- New endpoint `POST /search/image`: takes one uploaded photo, embeds it in memory with the same SigLIP2 model the text search uses, and returns the nearest spaces in the same shape as `GET /search`. The photo is never stored.
- Results drop anything below a minimum similarity (a non-interior photo returns an empty list), skip near-identical duplicates, and keep at most two spaces per project so one project cannot fill the page.
- Visitors only see published spaces; staff see every space (same rule as `/search`).
- The endpoint is rate-limited per client and rejects non-images, undecodable files and oversized uploads with a 4xx, never a 500.
- `/cong-trinh` gets a "Tìm bằng ảnh" button next to the text search; results show the uploaded photo's thumbnail and reuse the existing result grid.

Not in scope: room-type inference for the uploaded photo (results are style matches across room types; the optional `space_type` filter stays available), cleaning duplicate photos out of the library, image search inside the chat widget.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `space-similarity-search`: adds "Search By Uploaded Photo", covering minimum score, duplicate skipping, per-project cap, visibility, upload validation and rate limit.
- `space-discovery-ui`: adds "Photo Search On The Portfolio Page".

## Impact

- `backend/pipeline/search.py`: new `by_image()` beside `by_text()`, reusing `_embedder()` and `_query()`.
- `backend/api.py`: new `POST /search/image` route with `limit(...)`.
- `backend/ratelimit.py`: the shared 429 message becomes Vietnamese (chat and login show it too).
- `backend/tests/conftest.py`: the `drafts` fixture moves here from `test_review_workflow.py` so the API tests can publish a space temporarily.
- `src/api.js`: `searchByImage(file)`; `src/views/CongTrinhView.vue`: upload button, thumbnail, empty-result message.
- No schema change, no new dependency, no new model: SigLIP2, `python-multipart` and pgvector are already installed.
- Demo dependency: visitors see results only once spaces are published (`cms-publishing-workflow` task 6.2); today all 152 spaces are drafts.
