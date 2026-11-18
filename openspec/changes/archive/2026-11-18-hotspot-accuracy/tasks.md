# Tasks

## 1. Gemini names and points at items

- [x] 1.1 In `backend/pipeline/schemas.py`, add `AiItem {ten, loai, x, y}` and `SpaceClassificationResult.items: list[AiItem] = []`, and make `DetectedFurniture.bbox` / `confidence` optional with an optional `nguon_ai`. Verify that the existing schema readers still load stored hotspots (`pytest tests/test_hotspot_items.py`).
- [x] 1.2 In `backend/pipeline/multimodal_classifier.py`, add the items section to the prompt and the JSON example (design decisions 1–2), and parse `items` in `_normalize_parsed_data`: drop unknown `loai`, empty names and points outside 0–1000; convert `[y, x]`/1000 to `(x, y)`. The offline heuristic returns `items=[]`. Verify with no-network tests in `backend/tests/test_classifier_taxonomy.py` style: a canned answer with valid, invalid and out-of-range items parses to the expected list.

## 2. Merge, clean up, cap

- [x] 2.1 Create `backend/pipeline/hotspots.py` with `CLUTTER`, `FURNITURE`, the category → label map and `propose(detected, items)` (design decision 3). Verify with `backend/tests/test_hotspots_propose.py` (no GPU, no AI), one test per spec scenario: chandelier and rug from the AI become points without a box; the AI point replaces the box centre for a sofa; a lamp point inside a sofa box doesn't merge; an unmatched chair at 0.45 is dropped; two overlapping couches become one; bottles and cups are dropped; ten valid items give six, in the required order; no AI items gives detector-only, cleaned and capped.
- [x] 2.2 In `backend/pipeline/processor.py`, call `propose` after classification and save its result as the photo's hotspots; keep the raw detector counts. Verify with a test that processes one image with the detector and classifier stubbed and checks the saved hotspots (≤ 6, origin AI, `nguon_ai` set), and that `with_services` still gives the sofa a service.

## 3. Re-run for untouched drafts

- [x] 3.1 Create `backend/rebuild_hotspots.py` with `--dry-run`, `--limit N` and `--restore` (design decision 4): select untouched drafts, get items from the classifier, `propose` on the stored objects, write hotspots + a `review_log` `rebuild_hotspots` row with the previous objects, one transaction per photo; `--restore` puts back the logged objects for photos not edited since. Verify with DB tests (classifier stubbed): a hand-edited draft, a draft with a linked item and a published photo are unchanged; an untouched draft gets ≤ 6 points and a log row; a dry run changes nothing; restore brings back the previous objects.

## 4. Integration and docs

- [x] 4.1 On Docker: upload one living-room photo and check the hotspots on `/quan-tri` (fewer, on the items, including a lamp or rug where present); run `python rebuild_hotspots.py --dry-run`, then `--limit 5`, and compare 5 photos before and after on `/khong-gian/<id>`. Run the full `pytest` suite; only the already-known failures may remain.
- [x] 4.2 Update `TONG-QUAN-DU-AN.md`: UC17 (how hotspots are proposed, the re-run command) and section 11.4 scripts (`rebuild_hotspots.py`). Verify by reading the changed rows.

## Workflow follow-up

- Archive with `openspec-archive-change` after review.
