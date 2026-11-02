## Context

Every stored space has a 768-dim SigLIP2 image embedding (`space.embedding`), and `pipeline/search.py` already serves two queries over it: `similar_to` (space → spaces) and `by_text` (text → spaces), both through `_query`, which clamps to `MAX_K = 24` and applies the visitor/staff `published_only` rule. `VisionEmbedder.embed_image` accepts a path or a file object (`PIL.Image.open` takes either), and the model is loaded once per process by `search._embedder()`.

Spike on the real library (152 spaces, 8 projects, CPU):

| Query | Top-1 score |
|---|---|
| Library photo, cropped 80 %, resized, JPEG q60 | 0.89–0.97, original ranked first |
| Interior photos not in the library (`public/img/pic*.jpg`) | 0.70–0.92 |
| D3 logo / random noise / flat grey | 0.595 / 0.53 / 0.58 |

Also observed: top-5 is often five shots of one project; top-6 mixes 2–4 room types; nearest-other-neighbor score is 1.0 for at least 10 % of the library (duplicate photos); embedding one photo takes about 0.3 s on CPU after the model is loaded (first load about 30 s in the container).

## Goals / Non-Goals

**Goals:**
- Upload a photo, get the nearest spaces as cards, reusing the text-search result shape and grid.
- Return nothing rather than garbage for a non-interior photo.
- Keep the results varied: no single project or duplicate pair crowds them.
- Never store the visitor's photo; never 500 on a bad upload.

**Non-Goals:**
- Inferring the uploaded photo's room type (results are style matches; the optional `space_type` filter covers the rest).
- Removing duplicate photos from the library.
- Image search in the chat widget, drag-and-drop or paste (a file picker is enough for the demo).

## Decisions

### D1. Embed in memory with the existing model
Read the upload into bytes, wrap in `io.BytesIO`, call `_embedder().embed_image(buf)`. No new model, no change to `VisionEmbedder`. Alternatives: Vertex `multimodalembedding@001` (different vector space, would need re-embedding the library); saving the upload and reusing the ingest pipeline (stores visitor photos, runs YOLO + Gemini for nothing).

Starlette may spool uploads over 1 MB to a temporary file while parsing; that file is deleted when the request ends. The photo is never written under `image_d3/` or into the database.

### D2. `by_image` runs its own candidate query
`by_image(fp, space_type=None, k=6, published_only=False)` in `search.py` fetches up to `4 * MAX_K` candidates with the same WHERE clause as `_query`, plus `subfolder` and `embedding`, then filters in Python:

1. drop `score < MIN_IMAGE_SCORE`;
2. skip a candidate whose embedding has cosine ≥ `DUP_SCORE` with an already kept result;
3. skip a candidate whose `subfolder` (the project folder) already has `PER_PROJECT` kept results;
4. stop at `min(k, MAX_K)`.

It returns tuples whose first five fields match `_query` rows (`relative_path, space_type, design_style, score, id`), so `api._hit` serves both endpoints unchanged. Alternative: widen `_query` (extra columns, separate limit). That touches the two existing callers and the clamp for one new caller; a second small query is simpler.

### D3. Thresholds as module constants
`MIN_IMAGE_SCORE = 0.65` (between the logo at 0.595 and the lowest real interior at 0.70), `DUP_SCORE = 0.99` (true duplicates score 1.0, recompressed copies of one photo 0.89–0.97), `PER_PROJECT = 2`. Each gets a one-line comment with the measurement behind it, like `MIN_TEXT_SCORE` in `assistant.py`. Calibrated on 11 photos only, so a constant that is easy to move, not configuration.

### D4. Endpoint and validation
`POST /search/image` with `file: UploadFile`, optional form field `space_type`, optional query `k`, `user=Depends(optional_user)`, `dependencies=[Depends(limit("search_image", 10, 60))]`.

- Suffix not in `{.jpg, .jpeg, .png, .webp}` → 415 (same set as `/spaces/ingest`).
- Read `MAX_UPLOAD + 1` bytes (`MAX_UPLOAD = 8 MB`); longer → 413. nginx already allows 50 MB, so this check is the one users hit.
- `space_type` not in `SPACE_TYPES` → 422.
- `OSError` from decoding (covers `PIL.UnidentifiedImageError` and truncated files) and `PIL.Image.DecompressionBombError` → 415. Only the embed call is wrapped, so a database error still surfaces as a real error.
- Error `detail` strings are Vietnamese because the frontend shows `detail` verbatim; the shared 429 message in `ratelimit.py` becomes Vietnamese too (chat and login show it as well).

A sync `def` route, like `/search`: FastAPI runs it in the threadpool and the CPU-bound embed does not block the event loop.

### D5. Frontend
`searchByImage(file, k = 12)` in `src/api.js` posts `FormData` through the existing `request(..., { form })`. In `CongTrinhView.vue` a hidden `<input type="file" accept="image/jpeg,image/png,image/webp">` behind a "Tìm bằng ảnh" button; on change it stores an object URL for the thumbnail, sets `loading`, calls the API, and fills the same `hits` ref the text search uses, so the grid, count line and "Xóa" button are shared. The count line reads "N không gian giống ảnh của bạn"; an empty result reads "Không tìm thấy công trình giống ảnh này". "Xóa" shows whenever there are results, an error or a thumbnail (today it needs results, which would strand a failed photo search). Starting a text search or clearing revokes the object URL and drops the thumbnail. The input value is reset after each pick so choosing the same file again re-runs the search.

## Risks / Trade-offs

- [The 0.65 threshold rests on 11 photos; a dim or unusual interior may score below it] → constant with its measurement noted; `eval`-style recalibration once real visitor photos exist.
- [Visitors see nothing until spaces are published; today all 152 are drafts] → demo after `cms-publishing-workflow` task 6.2; staff see drafts meanwhile.
- [First search after a container start waits about 30 s for the model] → the busy state covers it; the model is shared with text search, so whichever runs first warms it.
- [Rate limit is per process and per client IP] → uvicorn runs with `--proxy-headers` in Docker, so the client IP is the visitor's, not nginx's; one worker, so per-process is per-app.
- [The candidate pool is 96 rows; once one or two projects hold most of a much larger library, the per-project cap can leave fewer than `k` results] → fine at 152 spaces / 8 projects; widen the pool or move the cap into SQL (`row_number() OVER (PARTITION BY subfolder)`) when that happens.
- [HEIC from a desktop is rejected] → 415 with a message asking for JPG/PNG/WEBP; iOS Safari converts library photos to JPEG on pick.

## Migration Plan

No schema or data change. Deploy is a backend and frontend rebuild (`docker compose up -d --build`). Rollback is reverting the commit.

## Open Questions

- None blocking. Room-type chips on the photo results can be added later without an API change (`space_type` is already accepted).
