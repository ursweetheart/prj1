## 1. Backend search

- [ ] 1.1 `search.labels` and similar-space reasons (design 1), and `ly_do` in `/spaces/{id}/similar`. Tests: shared style and tone give the right sentence; `khac` is never used; nothing shared gives an empty list.
- [ ] 1.2 Interior check and traits for `/search/image` (design 2), with the new response. Calibrate on Docker:
  - 20 library photos must pass;
  - a logo, a text screenshot, a portrait and a landscape must fail.

  Record the numbers in the design. Tests: refusal shape, traits shape, the confidence floor.
- [ ] 1.3 Description constraints, reasons and the weak hint for `/search` (design 3). Calibrate `WEAK_TEXT_SCORE` on 10 queries and record them. Tests:
  - "phòng khách …" filters living rooms and lists the constraint;
  - a synonym matches;
  - an explicit `space_type` wins;
  - reasons include a matching material;
  - a vague query carries the hint.

## 2. Project filter

- [ ] 2.1 `GET /projects/filter` (design 6). Tests: AND across dimensions and OR within one; counts; the loosening suggestion; each sort; only published projects.
- [ ] 2.2 `src/components/ProjectFilter.vue` plus `filterProjects` in `src/api.js`: accessible, 360 px. Not mounted (user decision). Add a vitest test for the query builder.

## 3. Frontend

- [ ] 3.1 `src/api.js`: response adaptation, `lastSearch` / `clearSearch`, `toCard` passes `ly_do`. `SpaceTile.vue` reason line. Add vitest tests.
- [ ] 3.2 `SearchNote.vue`, plus the one approved line in `SpacesView.vue`.
- [ ] 3.3 Explorer sort (design 7): `luot_xem_30` in `GET /spaces`, `useBrowse` sort with URL sync, the `FacetPanel` select.

## 4. Verification

- [ ] 4.1 Browser on Docker:
  - a similar section shows reasons;
  - a photo search shows the traits; a logo is refused;
  - "phòng khách gỗ sáng" shows "Đã lọc: Phòng khách" and reasons; "đẹp" shows the hint;
  - sorting works and stays in the URL;
  - `ProjectFilter` is checked by mounting it on a scratch page in dev only.

  Full `pytest` and `npm test` green.
