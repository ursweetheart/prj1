## 1. Search core

- [ ] 1.1 `pipeline/search.py`: constants `MIN_IMAGE_SCORE = 0.65`, `DUP_SCORE = 0.99`, `PER_PROJECT = 2`, each with the spike measurement in a comment
- [ ] 1.2 `by_image(fp, space_type=None, k=6, published_only=False)`: embed with `_embedder().embed_image(fp)`, fetch up to `4 * MAX_K` candidates (same WHERE as `_query`, plus `subfolder`, `embedding`), then drop below `MIN_IMAGE_SCORE`, skip duplicates (cosine ≥ `DUP_SCORE` with a kept result), cap `PER_PROJECT` per `subfolder`, stop at `min(k, MAX_K)`; rows keep `_query`'s first five fields
- [ ] 1.3 pytest (`tests/test_search.py`, needs DB): a cropped JPEG q60 copy of a stored photo ranks first its original or a stored duplicate of it (cosine ≥ `DUP_SCORE` with the original); a flat grey image returns `[]`; no `subfolder` appears more than twice; no two results have cosine ≥ `DUP_SCORE`; `space_type` filter holds

## 2. API

- [ ] 2.1 `api.py`: `POST /search/image` (`file`, form `space_type`, query `k`, `optional_user`, `limit("search_image", 10, 60)`); suffix check → 415, read `MAX_UPLOAD + 1` bytes (8 MB) → 413, unknown `space_type` → 422, decode errors (`OSError`, which covers `UnidentifiedImageError`, and `Image.DecompressionBombError`) around the embed call only → 415; Vietnamese `detail` strings; visitors `published_only=True`
- [ ] 2.2 `ratelimit.py`: 429 `detail` in Vietnamese ("Bạn thao tác quá nhanh, vui lòng thử lại sau.")
- [ ] 2.3 pytest (`tests/test_api.py`): staff upload returns hits in the `/search` shape; move the `drafts` fixture (with its `COLS`) from `tests/test_review_workflow.py` to `tests/conftest.py`, then with one draft set to `published` (restored by the fixture), a visitor searching with that space's own photo gets it back and no unpublished space; `.pdf` → 415; bytes named `photo.jpg` that are not an image → 415; 8 MB + 1 byte → 413; bad `space_type` → 422; the 11th request in a minute → 429 with `Retry-After`; file count under `image_d3/` and row count of `space` unchanged after a search

## 3. Frontend

- [ ] 3.1 `src/api.js`: `searchByImage(file, k = 12)` posting `FormData` (`file`) to `/search/image`
- [ ] 3.2 `CongTrinhView.vue`: "Tìm bằng ảnh" button over a hidden `<input type="file" accept="image/jpeg,image/png,image/webp">`; busy state disables both search buttons; thumbnail from an object URL; shared `hits` grid with "N không gian giống ảnh của bạn" / "Không tìm thấy công trình giống ảnh này"; errors in the existing `role="alert"` line
- [ ] 3.3 "Xóa" shows whenever results, an error or a thumbnail is present (today it needs `hits`); text search or "Xóa" revokes the object URL and removes the thumbnail; reset the input value after each pick so the same file can be searched again

## 4. Verify

- [ ] 4.1 With the DB up (`docker compose up -d db`): `python -m pytest tests/test_search.py tests/test_api.py tests/test_review_workflow.py tests/test_ratelimit.py` (the last-but-one guards the moved `drafts` fixture) and `npm test` pass
- [ ] 4.2 In Docker (`docker compose up -d --build`): signed in as staff, search with `public/img/pic3.jpg` and `public/img/logo.jpg` on `/cong-trinh`; the first shows cards with a thumbnail, the second shows the empty message; a text search afterwards removes the thumbnail
