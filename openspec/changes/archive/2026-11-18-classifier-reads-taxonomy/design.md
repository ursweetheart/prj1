# Design

## Context

See proposal.md for why. Current state that shapes the approach:

- `pipeline/taxonomy.py` already reads dimensions and values from `chieu_phan_loai` / `gia_tri_phan_loai`, falls back to `kb/taxonomy_seed.json`, and caches the result per process. The admin API calls `taxonomy.reload()` after every edit, merge and accepted candidate (`api.py:1097`, `:1401`). It does **not** expose `mo_ta` yet.
- The fixed room and style lists are read in five places, not three:
  1. `SYSTEM_PROMPT` (`multimodal_classifier.py:21-36`): codes, plus a one-line description for each of the 8 styles.
  2. `_normalize_parsed_data` (`:306-345`): room labels, spelling variants (`modern`, `minimalism`, `neo_classic` ...), and silent defaults `Hien_dai` / `phong_khach`.
  3. `Literal[...]` on `SpaceClassificationResult` (`schemas.py:35`, `:48`).
  4. `api.py:49-50` derive `SPACE_TYPES` / `STYLES` from those enums. They validate `/search`, `/search/image` (`space_type`) and the staff edit `PATCH /spaces/{id}` (`space_type`, `design_style`). **So today staff can't save a new value on the photo review page either.**
  5. `_heuristic_classify` (`:380-445`): folder-name rules returning fixed codes.
- The seed values all have an empty `mo_ta`. The only descriptions are the ones in `SYSTEM_PROMPT`.
- `seed_taxonomy.seed()` upserts values with `DO UPDATE SET ten=..., tu_dong_nghia=...`, so re-running it reverts staff renames and synonym edits.
- The `sync_ai_tags` trigger links `space.design_style` / `space_type` to `gia_tri_phan_loai.ma_dinh_danh`, so no trigger change is needed.
- "Photos where the AI was not sure" (`project_stats.py:160`) already counts style `Khac` and `style_confidence < 0.5`.

## Goals / Non-Goals

**Goals:**
- One source for the room and style lists: `taxonomy.labelled()`, used by the prompt, the normaliser, the result check, and the API validation.
- Re-running the seed is safe for staff edits, so it can be used to deploy the new descriptions.

**Non-Goals:**
- Using Gemini's structured-output `response_schema` with a dynamic enum. Prompt plus validation is enough and keeps the current call shape.
- Changing `backtag` in `discovery.py`, which already takes values as data.
- Letting the folder-name fallback learn new values.
- A "hidden" flag on values. Values can't be hidden today, only dimensions; merged values are deleted, so they drop out of the list automatically.

## Decisions

**1. Read through `pipeline/taxonomy.py`, not a new query in the classifier.**
Add `mo_ta` to `_from_db` / `_from_seed` / `_shape`, so `labelled()[dim]["values"][ma]` returns `{ten, mo_ta, syn}`. The classifier then gets the DB, the seed fallback and the cache for free.
*Alternative:* query `gia_tri_phan_loai` inside the classifier. Rejected because it would duplicate the fallback and miss `reload()`.

**2. Build the prompt's room and style sections from the taxonomy on every `classify` call.**
Keep `SYSTEM_PROMPT` as a template with two placeholders. The materials and SEO instructions stay fixed text. Each line reads `- <ma>: <ten>. <mo_ta>`. Building a short string per photo costs nothing next to the Gemini call, and it picks up edits after `reload()` without restarting the classifier.

**3. One matcher, used for Gemini answers and fallback answers alike.**
`resolve(dim, answer) -> ma | None` compares `taxonomy.fold(answer)` (with `-` and spaces folded to `_`) against each value's folded code, folded display name and folded synonyms, in that order. No match → the dimension's "Other" code (`khac` / `Khac`), and for style `design_style_confidence = 0.0`. The space label (`space_type_label`) comes from the value's `ten`.
*Alternative:* keep a fuzzy or nearest-match guess. Rejected because a silent wrong guess is exactly the bug being fixed.

**4. Plain `str` in `SpaceClassificationResult`, validated by the matcher.**
Pydantic `Literal` can't change at run time. The matcher guarantees a valid code before the model is built. `review_status` keeps its `Literal`.

**5. The API validates against the same list.**
Replace `SPACE_TYPES` / `STYLES` with `taxonomy.values("khong_gian")` / `taxonomy.values("phong_cach")` at request time (cached, so cheap). The 422 message keeps listing the allowed codes.

**6. Spelling variants become synonyms in the seed.**
The `style_map` variants (`modern`, `minimalism`, `minimalist`, `neo_classic`, `wabisabi` ...) go into `tu_dong_nghia`, and the `SYSTEM_PROMPT` descriptions go into `mo_ta`. Room labels already match `ten` closely enough. This also lets the assistant understand "modern" in chat (proposal, Impact).

**7. Seeding fills in, never overwrites, value data.**
On conflict, values keep their `ten`, `mo_ta` becomes `COALESCE(existing, seed)`, and synonyms become the union of both lists. Dimensions keep today's upsert. With this, `python seed_taxonomy.py` is the deploy step for the new descriptions and synonyms, and it can be re-run safely.
*Alternative:* a one-off SQL `UPDATE` in `schema.sql`. Rejected because the descriptions would then live in two files.

## Risks / Trade-offs

- **Weak or missing descriptions make Gemini pick worse values.** → A value without `mo_ta` is still listed by name, and the admin screen already edits `mo_ta`. NFR-10 (`eval_labels.py`) should be re-run once 30 or more photos are approved.
- **More photos land on `Khac`.** This is intended: they are now visible for review instead of silently wrong. → If it's frequent, add synonyms or a missing value from the taxonomy screen.
- **Stale cache in a separate process.** Scripts (`relabel.py`, `ingest_projects.py`) read the taxonomy fresh each run, and the API reloads after each edit. A long-running worker outside the API would keep an old list until restarted. There is no such worker today.
- **Removing the enums affects every import of `SpaceClassificationResult`.** Its only enum readers are `api.py:49-50` and `test_taxonomy_seed.py`, both handled in this change.
- **Synonym union can't remove a synonym through the seed.** That's acceptable: removing one is done on the admin screen.

## Migration Plan

1. Deploy the code and the updated seed file.
2. Run `docker compose exec backend python seed_taxonomy.py`. It fills empty descriptions and adds synonyms, and keeps staff edits.
3. Nothing else is needed: existing `space` rows already hold valid codes, and the trigger keeps their tags.

**Rollback:** revert the code. The added descriptions and synonyms are harmless to the old code.
