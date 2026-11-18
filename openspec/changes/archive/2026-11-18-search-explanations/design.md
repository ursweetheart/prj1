# Design

## Context

- **`pipeline/search.py`:**
  - `similar_to` keeps the same `space_type` (seq-2 rule);
  - `by_text(text, space_type)` embeds the whole sentence with the SigLIP2 text tower;
  - `by_image` drops hits under `MIN_IMAGE_SCORE = 0.65` (library interiors 0.70–0.92; a logo 0.595);
  - all return tuples, made into dicts by `_hit()` in `api.py`.
- **Frontend:**
  - `src/api.js` `searchSpaces` / `searchByImage` / `getSimilar` return arrays;
  - Tùng's `SpacesView.vue` / `SpaceView.vue` map them with `toCard` and render `SpaceTile` (a shared component);
  - the explorer's filters run in `useBrowse.js` + `FacetPanel.vue` (ours).
- **Data:** labels per photo are in `space_gia_tri` (all dimensions, synced from the `space_type` / `design_style` columns by trigger). Dimension and value names, codes and synonyms are in the taxonomy tables, with `taxonomy.fold` / `key` for accent-free matching. Projects are in `du_an` (`loai`, `dien_tich_m2`, `muc_dau_tu`).
- **Dependencies:** sorting by "newest" uses `space.ngay_xuat_ban` (publishing-workflow), and "most viewed" uses `tk_khong_gian_ngay` (tracking-pipeline). Both are applied first.

## Decisions

### 1. Reasons from shared labels

`labels(conn, ids) -> {id: {dim: [(code, name)]}}` reads `space_gia_tri`, joined to the visible dimensions in display order, without `khac`. For similar spaces: the intersection with the source, formatted "Cùng <dimension label> <value>" ("phong cách", "tông màu", ...; a short label map per dimension code, falling back to the dimension name), first 3. The hits gain `ly_do: [str]`.

### 2. Interior check and traits

- **Interior check** (SigLIP2 zero-shot): the photo's embedding is scored against the English prompts:
  - "a photo of an interior room";
  - "a logo", "a document or text", "a portrait of a person", "an outdoor landscape", "a product on a plain background".

  Softmax over the scaled scores. Not an interior when the room prompt is not the highest, or when the best library score is under `MIN_IMAGE_SCORE`. The prompt vectors are embedded once and cached. The threshold is checked during apply against the library and a few non-interiors.
- **Traits:** weighted kNN over the 15 nearest published library photos (weight = similarity). For style (`phong_cach`) and tone (`tong_mau`), confidence = winning weight / total weight. Traits under 0.4 are dropped.
- **Response:** `{noi_that, dac_diem: {phong_cach?: {ma, ten, do_tin_cay}, tong_mau?: {...}}, ket_qua: [...]}`.

### 3. Description constraints

1. Fold the query.
2. For `khong_gian` and `phong_cach`, find every value whose folded name, code or synonym occurs as a whole-word phrase (longest first, no overlaps). The first match per dimension becomes a hard filter (`space_type` / `design_style`), and its words are removed.
3. Embed the remainder, or the whole query if nothing is left.
4. Reasons: the hit's labels whose folded name, or any folded synonym, occurs in the query, plus the constraint values.
5. Weak hint: when the best score is under `WEAK_TEXT_SCORE`, calibrated during apply on 10 sample queries (SigLIP text-image scores are on another scale than image-image).
6. **Response:** `{rang_buoc: [{chieu, ma, ten}], goi_y: str|null, ket_qua: [...]}`. An explicit `space_type` parameter still wins.

### 4. API compatibility

`/search` and `/search/image` return the object. `src/api.js`:
- `searchSpaces` / `searchByImage` return `res.ket_qua`, with the other fields copied onto a module-level reactive `lastSearch` (`{kind, rang_buoc, goi_y, noi_that, dac_diem}`);
- `clearSearch()` resets it;
- `toCard` passes `ly_do`.

Tùng's views keep calling them the same way.

### 5. `SearchNote.vue`

It reads `lastSearch`, renders the sentences in an `aria-live="polite"` block, and is inserted once in `SpacesView.vue` above the results.

`SpaceTile.vue` renders `space.ly_do` joined by " · " in a small line when present.

### 6. `GET /projects/filter`

- **Parameters:** `phong_cach[]`, `loai_cong_trinh[]`, `muc_dau_tu[]`, `dien_tich_tu`, `dien_tich_den`, `sap_xep` (`moi_nhat` | `dien_tich` | `xem_nhieu`), `limit` ≤ 60.
- **Query:**
  1. Published projects: `du_an` with ≥ 1 published space.
  2. Each project's value sets come from its published spaces' `space_gia_tri`, plus `du_an.loai` mapped to `loai_cong_trinh` (where the code matches) and `du_an.muc_dau_tu`.
  3. Filtering and counting happen in Python over that small set (64 projects), which keeps the code simple.
- **Counts:** for value v of dimension d, count with d's selection replaced by {v}.
- **Loosening:** when the result is empty, try dropping each active dimension and pick the largest count.
- **Sort:** `max(ngay_xuat_ban)`, `dien_tich_m2`, or 30-day views from `tk_khong_gian_ngay`.
- **Returns:** `{tong, du_an: [{slug, ten, anh_bia, loai, dien_tich_m2, ...}], dem: {dim: {value: n}}, noi_long?: {chieu, ten, so_du_an}}`.

`ProjectFilter.vue` takes no props, emits `results`, and is not mounted anywhere (the user's decision).

### 7. Explorer sort

`useBrowse.js` gains `sort` (synced to the URL query `sap_xep`) and orders the filtered list client-side:
- newest by `ngay_xuat_ban`;
- most viewed by `luot_xem_30` (added to `GET /spaces` items for published photos from `tk_khong_gian_ngay`);
- style by name.

`FacetPanel.vue` gets a labelled `<select>`.

## Risks / Trade-offs

- **[Zero-shot interior check misfires]** It is combined with the calibrated similarity floor, and the refusal only blocks results, never the visitor.
- **[kNN traits mirror the library's labels]** They describe the photo in the studio's own vocabulary, which is the goal. Low-confidence traits are hidden.
- **[Response shape change]** Only `src/api.js` reads these endpoints, and it adapts them.
