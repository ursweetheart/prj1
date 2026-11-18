# Proposal

## Why

On the review page (`/quan-tri`), staff set a photo's room type and style with dropdowns built from a fixed list in `src/api.js:223-224`. They can only pick what's already there, and there's no way to say "this photo is a style we don't have yet". Adding a value is only possible for the lead architect, on a separate screen.

If reviewers could freely type new values, the list would fill with typos and duplicates ("Japandy", "japandi ", "Nhật Bắc Âu" for Japandi), and new values would arrive with no description, which the AI tagger needs (see `classifier-reads-taxonomy`).

## What Changes

- On the review page, the room type and style dropdowns become **typing fields with suggestions**, like fish shell. The best match appears as grey text (Tab or → accepts it), with a short ranked list of other matches underneath. Matching ignores accents and case and covers code, display name and synonyms.
- Matches are ranked: name starts with the typed text, then a synonym starts with it, then the name contains it; ties go to the value used on the most photos.
- If the typed word matches nothing, the reviewer can **suggest it as a new value**:
  1. A local spelling check offers "Did you mean …?" for near matches ("Japandy" → Japandi).
  2. Otherwise Gemini receives the photo, what we already know about it (caption, materials, colours, detected objects), the typed word, and the current values with descriptions. It answers whether the word means an existing value, and if not, drafts a description and synonyms.
  3. If Gemini says it's an existing value, the reviewer is offered that value. Otherwise a **value suggestion** is saved for the lead architect, and the photo's field is set to "Other" (`Khac` / `khac`) until a decision.
- The lead architect sees value suggestions at `/quan-tri/phan-loai?tab=de-xuat`, next to the dimension suggestions. They can edit the name, description and synonyms, then accept or reject.
  - **Accept** creates the value and moves every photo waiting on it to the new value.
  - **Map to an existing value** adds the typed word as a synonym of that value and moves the waiting photos to it, so the next reviewer's autocomplete understands the word.
  - **Reject** leaves those photos as "Other".
- Suggesting the same word again (ignoring accents and case) adds the photo to the existing suggestion instead of creating a second one.
- Out of scope: the other dimensions on the review page (`loai_cong_trinh`, `muc_dau_tu` ...), which keep their dropdowns, and creating values directly from the review page, even for the lead architect.

## Capabilities

### New Capabilities

- `taxonomy/value-suggestions`: typing a room type or style with ranked suggestions on the review page, suggesting a new value with an AI duplicate check and drafted description, and the lead architect's accept / reject of value suggestions.

### Modified Capabilities

None. Taxonomy admin's rule that only approvers add values stays as it is. Values still only become live through an approver.

## Impact

- **Depends on `classifier-reads-taxonomy`:** the API must accept values from the database (`PATCH /spaces/{id}`), and the AI tagger must use new values and their descriptions.
- **Frontend:** `src/views/ReviewView.vue` (two `<select>` replaced by a new typing component), a new `src/components/TagInput.vue`, `src/components/TaxonomyCandidates.vue` (value suggestions section), and `src/api.js` (new calls; the room and style options come from `GET /taxonomy` instead of `SPACE_TYPES` / `STYLES`).
- **Backend:** `api.py`: a new suggest endpoint for staff, value-suggestion listing and accept / reject for approvers, and usage counts on the taxonomy list. New `pipeline/value_suggest.py` (spelling check, Gemini check, candidate upsert).
- **Data:** reuses `ung_vien_phan_loai` with `loai = 'gia_tri'` (already allowed by the table's check constraint). No new table; the photos waiting on a suggestion are kept in `bang_chung`.
- **AI cost:** one Gemini call per new word suggested (never per keystroke), rate-limited.
