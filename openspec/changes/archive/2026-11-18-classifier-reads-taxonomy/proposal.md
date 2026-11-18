# Proposal

## Why

The AI tagger that labels every uploaded photo still uses fixed lists of room types and styles written into the code, in three places: the Gemini prompt (`SYSTEM_PROMPT` in `pipeline/multimodal_classifier.py`), the answer normaliser (`_normalize_parsed_data`), and the `Literal[...]` enums in `pipeline/schemas.py`. If staff add a value at `/quan-tri/phan-loai`, the AI can never pick it. Worse, any answer the normaliser doesn't recognise quietly becomes `Hien_dai` (styles) or `phong_khach` (rooms), so wrong tags look confident and nobody is asked to check them.

The `taxonomy/data-driven-taxonomy` spec already requires classification to read allowed values from data (NFR-13). This is the last part still hard-coded (roadmap 1.1, remaining item).

## What Changes

- The classifier reads the allowed values for `khong_gian` (room type) and `phong_cach` (style) from `gia_tri_phan_loai` through `pipeline/taxonomy.py`, which falls back to `kb/taxonomy_seed.json` when the database can't be reached.
- The Gemini prompt is built from those values at run time, using each value's code, display name (`ten`) and description (`mo_ta`).
- Gemini's answer is matched against the same list by code, display name, or synonym (`tu_dong_nghia`), all compared without accents or case.
- **BREAKING (behaviour):** an answer that matches nothing becomes `Khac` / `khac` ("Other") with style confidence 0, instead of `Hien_dai` / `phong_khach`. These photos then show up in the existing "AI not sure" review hints.
- The `Literal[...]` enums on `SpaceClassificationResult.space_type` / `design_style` become plain strings, checked against the taxonomy.
- The style descriptions and spelling variants now in the prompt and normaliser move into the data: descriptions go into `mo_ta` in the seed and existing rows, and variants such as `modern` and `minimalism` become synonyms.
- The API checks room type and style against the same stored values. Today `PATCH /spaces/{id}`, `/search` and `/search/image` reject any value not in the code enums (`api.py:49-50`), so staff can't even save a new style by hand on the review page.
- Re-running `seed_taxonomy.py` fills in empty data and keeps staff edits, instead of overwriting display names and synonyms.
- The folder-name fallback (`_heuristic_classify`) keeps its rules, but its answer is checked the same way, so a merged-away code falls back to `Khac` / `khac`.
- Out of scope: re-tagging photos already in the library when a value is added (still done by running `relabel.py`), and the other dimensions (`tong_mau`, `vat_lieu`, `loai_cong_trinh`, `muc_dau_tu`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `taxonomy/data-driven-taxonomy`: adds two requirements. "Automatic Tagging Uses Stored Values" covers choosing room type and style from the stored values, guided by their descriptions. "Unmatched Answers Fall Back to Other" covers unmatched answers falling back to "Other" and being flagged for review.

## Impact

- **Code:** `backend/pipeline/multimodal_classifier.py` (prompt, normaliser, fallback), `backend/pipeline/schemas.py` (enums removed), `backend/pipeline/taxonomy.py` (also exposes `mo_ta`), `backend/api.py` (validation in `/search`, `/search/image`, `PATCH /spaces/{id}`).
- **Data:** `backend/kb/taxonomy_seed.json` gets `mo_ta` and synonyms for the `phong_cach` / `khong_gian` values. `seed_taxonomy.py` changes to fill-only for values: keep `ten`, fill an empty `mo_ta`, add synonyms.
- **Tests:** `tests/test_taxonomy_seed.py::test_seed_matches_current_literals` compares against the enums being removed, so it is replaced. New classifier tests cover a new value, a synonym, and an unknown answer.
- **Callers unchanged:** `pipeline/processor.py`, `relabel.py`, `ingest_projects.py` and `generate_kb.py` keep calling `MultimodalClassifier.classify` the same way. The `sync_ai_tags` database trigger already matches `space.design_style` / `space_type` to `gia_tri_phan_loai.ma_dinh_danh`, so a new value's tag is linked automatically.
- **Chat:** new synonyms are also used by the assistant's request parsing (`taxonomy.synonym_map`). That is intended, since a customer typing "modern" means `Hien_dai`.
