# Design

## Context

See proposal.md for why, and `specs/taxonomy/value-suggestions/spec.md` for the behaviour. Current state that shapes the approach:

- `ReviewView.vue:92-96` renders room type and style as `<select>` over `SPACE_TYPES` / `STYLES` from `src/api.js:223-224` (fixed lists). Saving goes through `PATCH /spaces/{id}` (STAFF + content), which writes `review_log` and fires `sync_ai_tags`.
- `GET /taxonomy` (public) returns values with `id, ma_dinh_danh, ten, tu_dong_nghia`, but no usage counts. `/taxonomy/admin` has counts but is approver-only.
- `ung_vien_phan_loai` already allows `loai = 'gia_tri'`. Its listing, accept and reject endpoints (`api.py:1342-1410`) and `_pending` only handle `loai = 'chieu'`.
- `taxonomy_admin.add_value` / `edit_value` already create and edit values with code generation, synonym cleaning and the `nhat_ky_phan_loai` log.
- Photo + facts → Gemini is already done in `generate_transcripts.py:55-56`: `MultimodalClassifier._prepare_image_payload` plus `vertex.generate(parts)`.
- `ratelimit.limit(name, n, seconds)` exists and is used on `/search/image`.
- This change assumes `classifier-reads-taxonomy` is applied: `PATCH /spaces/{id}` validates against the database, and `taxonomy.labelled()` carries `mo_ta`.

## Goals / Non-Goals

**Goals:**
- No server call per keystroke. Matching runs in the browser over a list loaded once.
- One endpoint handles "suggest a word". It does the spelling check, the AI check and saving, so the browser can't skip a step.
- Reuse the candidate table, the taxonomy admin functions and the suggestions tab. No new table.

**Non-Goals:**
- The other dimensions' dropdowns (per photo and per project). Those values are set by people and rarely need new values.
- An undo history of what the photo held before it became "Other".
- Fuzzy matching while typing (only prefix / contains). Near spellings are caught when the reviewer suggests the word.

## Decisions

**1. Match in the browser; add usage counts for staff to `GET /taxonomy`.**
The list is small (about 20 values for these two dimensions), so a client-side filter is instant. `GET /taxonomy` adds `so_anh` (number of spaces carrying the value, from `space_gia_tri`) **only when the caller is staff**, so visitors don't see how many draft photos exist. Folding mirrors `taxonomy.fold` (`NFD`, drop marks, `đ→d`) as one small helper in `src/lib/`, with spaces, `-` and `_` treated alike.
*Alternative:* a `/taxonomy/suggest?q=` endpoint. Rejected because it means a request per keystroke for a list that fits in memory.

**2. `TagInput.vue`: an ARIA 1.2 combobox with inline completion.**
`<input role="combobox" aria-autocomplete="both" aria-expanded aria-controls aria-activedescendant>` plus a `role="listbox"` list. The grey completion is a hidden copy of the typed text followed by the rest of the best match, layered behind a transparent input so it lines up with any font. Keys:
- Tab or → (at the end of the text) accepts the completion.
- ↑/↓ move through the list; Enter picks.
- Esc closes the list.
- Leaving the field without picking restores the saved value.

On touch screens there's no Tab, so tapping a list item does the same. The last list row is "+ Suggest "<text>"" when nothing matches exactly. Only room type and style use it; the props are `dimension`, `modelValue` (code) and `values`.

**3. One endpoint: `POST /spaces/{id}/suggest-value {chieu, text, force}`.**
Roles are the same as `PATCH /spaces/{id}`; `chieu` must be `khong_gian` or `phong_cach`. Steps, in order:
1. **Exact fold match** to a code, name or synonym → `{kind: "existing", ma, source: "exact"}`. A safety net in case the browser list was stale.
2. **Existing undecided suggestion with the same key** → add the space to it, set the photo to "Other" → `{kind: "suggested", id}`. No AI call.
3. **Spelling check** with `difflib.get_close_matches` (cutoff 0.8) over folded names and synonyms → `{kind: "existing", ma, source: "spelling"}`. Skipped when `force`.
4. **AI check** (rate limit `suggest_value` 10/60s per user): send the photo, its caption, materials, palette and hotspot labels, the typed word, and the dimension's values with descriptions. Gemini returns JSON `{trung_voi: <code>|null, ly_do, mo_ta, tu_dong_nghia[]}`. A `trung_voi` that isn't a current code is treated as null. If `trung_voi` is set and not `force` → `{kind: "existing", ma, source: "ai", ly_do}`, and the draft is kept in the response so a `force` resend doesn't need a second call.
5. **Save** the suggestion and set the photo's field to "Other" (same write path as `PATCH`, so `review_log` and tags follow) → `{kind: "suggested", id}`.

If Vertex is unavailable, times out (20 s) or returns bad JSON, step 4 is skipped and step 5 saves without a description.
*Alternative:* run the AI check in the background after saving. Rejected because the "Did you mean …?" answer would arrive after the reviewer has moved on. A few seconds with a spinner, only for genuinely new words, is acceptable.

**4. Storage in `ung_vien_phan_loai`.**
- `loai = 'gia_tri'`
- `ten_de_xuat` = the first typed text
- `bang_chung = {chieu, khoa, space_ids[], nguoi_de_xuat[], mo_ta, tu_dong_nghia, ai: {ly_do, trung_voi}}`, where `khoa` is the folded key (spaces, `-` and `_` removed)

A partial unique index on `((bang_chung->>'chieu'), (bang_chung->>'khoa')) WHERE loai = 'gia_tri' AND trang_thai = 'cho_duyet'` stops two reviewers creating twins. The insert uses `ON CONFLICT DO UPDATE` to append the space id. The review list query adds `cho_duyet_gia_tri` per space (`bang_chung->'space_ids' @> to_jsonb(id)`), so the card can show "Waiting for approval: …".

**5. Approver endpoints alongside the dimension ones.**
- `GET /taxonomy/candidates` gains a `gia_tri` array: id, dimension, text, draft description and synonyms, AI reason, and the waiting spaces as thumbnails. The existing `candidates` key is unchanged, so `TaxonomyCandidates.vue` keeps working.
- `POST /taxonomy/value-candidates/{id}/accept {ten, mo_ta, tu_dong_nghia}` calls `taxonomy_admin.add_value`; 409 if the code exists.
- `.../{id}/map {gia_tri_id}` calls `taxonomy_admin.edit_value`, adding the text as a synonym.
- `.../{id}/reject`.

Accept and map then run `UPDATE space SET <column> = <code> WHERE id = ANY(space_ids) AND <column> = <Other code>`. The column is `design_style` for `phong_cach` and `space_type` for `khong_gian`. Photos someone changed in the meantime are left alone. One transaction per decision, then `taxonomy.reload()`. `_pending` takes a `loai` argument.

**6. The AI prompt describes the dimension, not just the photo.**
The prompt asks Gemini to describe what the *style or room type* means in general, using the photo only as an example, so `mo_ta` isn't a description of one room (see Risks). Its text sits next to `BACKTAG_PROMPT`'s style in `pipeline/value_suggest.py`.

## Risks / Trade-offs

- **[The AI wrongly says a new word is an existing value]** → The reviewer sees the reason and can send anyway (`force`), and the approver can still accept.
- **[The AI-drafted description is shaped by one photo]** → The prompt asks for a general definition, and the approver edits it before accepting. The draft is clearly an AI draft.
- **[A photo sits on "Other" until an approver acts]** → The card shows what it's waiting for, and the suggestions tab shows how many photos wait on each. That's the price of keeping the list clean.
- **[Reject leaves photos on "Other"]** → Intended: the reviewer already said none of the existing values fit. They show in the "AI not sure" hints for another look.
- **[Ghost text misaligned with unusual fonts or zoom]** → The layered copy uses the input's own computed font, and the list below always shows the full name, so nothing depends on the ghost alone.
- **[Gemini cost]** → One call per new word per dimension, only when there is no undecided suggestion with the same key; 10 per minute per user.

## Migration Plan

1. Apply after `classifier-reads-taxonomy`.
2. The partial unique index goes into `schema.sql` (idempotent `CREATE UNIQUE INDEX IF NOT EXISTS`). No data migration.

**Rollback:** revert the code. Leftover `loai = 'gia_tri'` rows are ignored by the old listing.
