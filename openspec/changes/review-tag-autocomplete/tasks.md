# Tasks

Prerequisite: `classifier-reads-taxonomy` is applied (API validates against the database; `taxonomy.labelled()` has `mo_ta`).

## 1. Matching and ranking (browser, no UI yet)

- [x] 1.1 Add `src/lib/tagMatch.js`: `fold(s)`, mirroring `pipeline/taxonomy.fold` (NFD, drop marks, `đ→d`, lower case, spaces, `-` and `_` treated alike), and `rank(values, typed, limit = 6)`. Ranking: name prefix, then synonym prefix, then name contains; ties broken by `so_anh` descending. Verify with `src/lib/tagMatch.test.js` (`npm test`): "Ja" → Japandi first; "hien" and "modern" → Hiện đại; "t" → Tân cổ điển and Tối giản ordered by `so_anh`; "dien" lists a prefix match before Tân cổ điển; "xyz" → empty.

## 2. Usage counts and the typing field

- [x] 2.1 In `GET /taxonomy` (`backend/api.py:1070`), add `so_anh` per value only when the caller is staff (`optional_user`). Verify with an API test: staff get counts, an anonymous request gets no `so_anh` key.
- [ ] 2.2 Build `src/components/TagInput.vue` (ARIA combobox, design decision 2): grey inline completion, list of up to 6, Tab or → / ↑ ↓ / Enter / Esc, restore on blur without a pick, last row "+ Gợi ý "<text>"" when nothing matches exactly, and emits `update:modelValue` (code) and `suggest` (text). Verify by keyboard only and with Chromium touch emulation at 360px: complete "Ja" with Tab, pick the second match with ↓ Enter, Esc then blur restores the value. The accessibility tree should show combobox / listbox / option.
- [ ] 2.3 In `src/views/ReviewView.vue:92-96`, replace the room type and style `<select>` with `TagInput`, fed from `getTaxonomy()` (`khong_gian` / `phong_cach` values with `so_anh`). Stop importing `SPACE_TYPES` / `STYLES` there, and remove them from `src/api.js:223-224` if nothing else uses them (`grep -rn "SPACE_TYPES\|STYLES" src`). Verify: changing a photo's style by typing and saving it updates the photo as before (the existing review tests pass).

## 3. Suggest endpoint and AI check

- [x] 3.1 Add the partial unique index on `ung_vien_phan_loai ((bang_chung->>'chieu'), (bang_chung->>'khoa')) WHERE loai = 'gia_tri' AND trang_thai = 'cho_duyet'` to `backend/schema.sql` (idempotent). Verify that `schema.sql` applies twice without error.
- [x] 3.2 Create `backend/pipeline/value_suggest.py`: `key(text)`, `exact(dim, text)`, `spelling(dim, text)` (`difflib`, cutoff 0.8), `ai_check(space, dim, text)` (photo + caption, materials, palette and hotspot labels + values with `mo_ta`, using the `generate_transcripts.py:55-56` pattern; a `trung_voi` outside the current codes becomes `None`; any Vertex error returns `None`), and `upsert(conn, dim, text, space_id, user_id, draft)`. Verify with tests that need no network (monkeypatch `vertex.generate`): "Japandy" → Japandi by spelling; "mid century" and "Mid-century" give the same key; an invented `trung_voi` is dropped; a raised Vertex error gives `None`.
- [x] 3.3 Add `POST /spaces/{id}/suggest-value {chieu, text, force}` in `backend/api.py` (design decision 3: exact → existing suggestion → spelling → AI → save). Use the same roles as `PATCH /spaces/{id}`, the `limit("suggest_value", 10, 60)` rate limit on the AI path only, 422 for any other `chieu`, and set the photo to `Khac` / `khac` through the existing edit path so `review_log` and tags follow. Verify with API tests for every spec scenario under "Suggest a New Value", "One Suggestion per Word" and "Who Can Suggest" (401 anonymous, 429 on the 11th AI check).
- [ ] 3.4 Include `cho_duyet_gia_tri` (pending suggestion text per dimension) in the review list rows, and show "Chờ duyệt: <text>" on the photo's card in `ReviewView.vue`. Wire `TagInput`'s `suggest` to the endpoint: a spinner while waiting; "Có phải ý bạn là <ten>?" with the AI reason, a use button and a "Vẫn gợi ý" button (`force`) for `existing`; and the note for `suggested`. Verify on Docker: suggesting "Japandy" offers Japandi, and a new word leaves the card showing the note and the field showing "Khác".

## 4. Approver decisions

- [x] 4.1 Generalise `_pending` to take `loai`; add a `gia_tri` array to `GET /taxonomy/candidates`; add `POST /taxonomy/value-candidates/{id}/accept|map|reject` (design decision 5), reusing `taxonomy_admin.add_value` / `edit_value`, updating only waiting photos still on "Other", then `taxonomy.reload()`. Verify with API tests for every scenario under "Approver Decides Value Suggestions" (accept, a photo changed while waiting, 409 name taken, map adds the synonym, reject, 403 for an architect).
- [ ] 4.2 Add a "Giá trị được gợi ý" section to `src/components/TaxonomyCandidates.vue`: per suggestion, the dimension, waiting photo thumbnails, editable name, description and synonyms prefilled from the AI draft (marked as AI draft), and Accept / Map to (a `TagInput` over that dimension) / Reject with confirmation. Verify on Docker as lead architect: accepting "Mid-century" moves its waiting photos to the new value and the value appears in the review page's autocomplete without reloading the backend.

## 5. Integration and docs

- [ ] 5.1 End-to-end on Docker: an architect types a new style on two photos (one "Mid-century", one "mid century"), sees one suggestion with both photos, the lead architect accepts it, and a newly uploaded matching photo is tagged with it by the AI (via `classifier-reads-taxonomy`). Run the full `pytest` suite and `npm test` green.
- [x] 5.2 Update `TONG-QUAN-DU-AN.md`: UC13 (Gắn nhãn không gian) row (typing with suggestions, value suggestions), UC15 (value suggestions on the suggestions tab), section 11.2 API table (new endpoints). Verify by reading the changed rows.

## Workflow follow-up

- Archive with `openspec-archive-change` after review, after `classifier-reads-taxonomy` is archived.
