## 1. Backend search

- [x] 1.1 `search.labels` and similar-space reasons (design 1), and `ly_do` in `/spaces/{id}/similar`. Tests: shared style and tone give the right sentence; `khac` is never used; nothing shared gives an empty list.
- [x] 1.2 Interior check and traits for `/search/image` (design 2), with the new response. Calibrate on Docker:
  - 20 library photos must pass;
  - a logo, a text screenshot, a portrait and a landscape must fail.

  Record the numbers in the design. Tests: refusal shape, traits shape, the confidence floor.
- [x] 1.3 Description constraints, reasons and the weak hint for `/search` (design 3). Calibrate `WEAK_TEXT_SCORE` on 10 queries and record them. Tests:
  - "phòng khách …" filters living rooms and lists the constraint;
  - a synonym matches;
  - an explicit `space_type` wins;
  - reasons include a matching material;
  - a vague query carries the hint.

## 2. Project filter

- [x] 2.1 `GET /projects/filter` (design 6). Tests: AND across dimensions and OR within one; counts; the loosening suggestion; each sort; only published projects.
- [x] 2.2 `src/components/ProjectFilter.vue` plus `filterProjects` in `src/api.js`: accessible, 360 px. Not mounted (user decision). Add a vitest test for the query builder.

## 3. Frontend

- [x] 3.1 `src/api.js`: response adaptation, `lastSearch` / `clearSearch`, `toCard` passes `ly_do`. `SpaceTile.vue` reason line. Add vitest tests.
- [x] 3.2 `SearchNote.vue`, plus the one approved line in `SpacesView.vue`.
- [x] 3.3 Explorer sort (design 7): `luot_xem_30` in `GET /spaces`, `useBrowse` sort with URL sync, the `FacetPanel` select.

## 4. Verification

- [x] 4.1 Browser on Docker:
  - a similar section shows reasons;
  - a photo search shows the traits; a logo is refused;
  - "phòng khách gỗ sáng" shows "Đã lọc: Phòng khách" and reasons; "đẹp" shows the hint;
  - sorting works and stays in the URL;
  - `ProjectFilter` is checked by mounting it on a scratch page in dev only.

  Full `pytest` and `npm test` green.

## Results (2026-11-18)

- **Interior check calibration (1.2):**
  - zero-shot interior share: 20 random library photos scored at least 0.924 (median 0.985); a logo, a second logo, a text screenshot, a flat grey image and noise scored 0.012 or less;
  - threshold `INTERIOR_MIN = 0.5`, combined with the earlier similarity floor (0.65);
  - no portrait or landscape photo was available to test.
- **Weak-hint calibration (1.3):**
  - SigLIP text–photo scores were 0.03–0.16, too close to separate good queries from bad ones;
  - the hint is therefore given when there are no results, or when the description named no room type or style and its best match scores under `WEAK_TEXT_SCORE = 0.10`;
  - on 11 queries this flagged "đẹp" (0.088), "xe hơi màu đỏ" (0.033), "con mèo" (0.053) and "abc xyz" (0.060), and none of the real ones ("nhà" 0.117 passes).
- **Design change found while measuring:** the folded, accent-free remainder embedded badly, so the remaining words are now cut from the original text and keep their accents.
- **Browser, headless:**
  - the similar section shows "Cùng loại phòng Phòng ngủ master · Cùng phong cách Indochine · Cùng tông màu Ấm";
  - an Indochine photo gives "Ảnh của bạn có vẻ thuộc phong cách Indochine, tông màu Ấm."; the logo is refused politely; clearing removes the note;
  - "phòng khách gỗ sáng" shows "Đã lọc: Phòng khách", with reasons "Phòng khách · Sáng · Gỗ"; "đẹp" shows the hint;
  - sorting by most viewed puts the store's most viewed photo first, is kept in the URL (`#sap_xep=xem_nhieu`) and survives a reload;
  - no horizontal scroll at 360px.
- **`ProjectFilter.vue`:** checked on a temporary route, which was removed afterwards. It shows 9 projects with counts; a value can be toggled by keyboard (2 projects); an area of at least 5000 m² offers "Bỏ lọc Diện tích: 2 dự án" and applying it works; it fits at 360px.
- **Tests:** `pytest` 518 passed (3 known environment failures); `npm test` 88 passed.
