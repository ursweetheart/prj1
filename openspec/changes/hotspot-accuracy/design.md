# Design

## Context

See proposal.md for the measurements and `specs/hotspot-detection/spec.md` for the behaviour.

- `pipeline/processor.py` → `process_image`:
  1. `FurnitureDetector.detect` (YOLO v8s, COCO, `conf ≥ 0.25`) returns `FurnitureDetectionResult.objects`, each with `label`, `label_vi`, `confidence`, `bbox` and `hotspot_anchor` = box centre.
  2. `MultimodalClassifier.classify` sends the photo and the detection counts to Gemini in one call.
  3. `store.save_records` writes `furniture_detection` as `space.hotspots`.
- Readers of `space.hotspots.objects`:
  - `hotspotsOf` (`src/api.js`, visitor page) and `HotspotEditor.vue`: use `hotspot_anchor` and `label_vi`.
  - `with_services` (`pipeline/assistant.py`): maps services by `label` (`couch`, `bed`, `dining table`…).
  - `items.py`: hand edits; `nguon_tao` `'ai'` when absent, or `'thu_cong'`. A point keeps its box and confidence when moved.
  - `relabel.py`: drops `thu_cong` points before classifying.
- `DetectedFurniture.bbox` is required today. A hand-made point is stored without one through `items.py`'s own path.

## Goals / Non-Goals

**Goals:**
- Better points at no extra AI cost at upload: they ride on the existing classification call.
- One pure function decides the final hotspots, so it can be tested without a GPU or the AI.

**Non-Goals:**
- Replacing YOLO or training a model.
- Changing hand editing, the item library, or the visitor's hotspot card.
- Touching photos past draft, or any hand-edited hotspots.

## Decisions

**1. Gemini returns `items` in the classification answer.**
The prompt gains a section asking for up to 8 main interior items (not small decor or clutter). Each is `{"ten": "<Vietnamese name>", "loai": <one of a fixed list>, "diem": [y, x]}`, with the point **on the item** in Gemini's 0–1000 convention, y first. `SpaceClassificationResult` gains `items: list[AiItem]` (default `[]`). Parsing drops entries with a missing or unknown `loai`, an empty name, or a point outside 0–1000, then converts the point to 0–1 `(x, y)`.
*Alternative:* ask Gemini for boxes (`box_2d`). Rejected because a box centre is exactly today's problem. A point on the item is what a hotspot needs, and the detector already gives boxes where it can.

**2. Fixed categories, mapped to detector labels where possible.**
`loai` ∈ `sofa, ghe, giuong, ban, tu, ke, den, thao, rem, guong, tranh, cay, tv, bep, bon_rua, tu_lanh, khac`. Those with a COCO equivalent take its label (`sofa→couch`, `ghe→chair`, `giuong→bed`, `ban→dining table`, `tv→tv`, `bep→oven`, `bon_rua→sink`, `tu_lanh→refrigerator`, `cay→potted plant`), so `with_services` keeps mapping services. The others use `loai` itself as `label`. Matching a Gemini item to a box also requires compatible categories, so a lamp point inside a sofa box doesn't merge with the sofa.

**3. `pipeline/hotspots.py`: `propose(detected: list[DetectedFurniture], items: list[AiItem]) -> list[DetectedFurniture]`.**
1. Drop detector objects whose label is in `CLUTTER` (bottle, cup, bowl, book, wine glass, fork, knife, spoon, remote, cell phone, person, laptop, mouse, keyboard, scissors, toothbrush) or that are below 0.4.
2. Drop duplicates: same label, intersection > 50% of the smaller box; keep the higher confidence.
3. For each AI item, take the smallest compatible box containing its point. **Merged:** AI name and point, box, confidence and label from the box, `nguon_ai='ca_hai'`. A box is used once.
4. **AI-only items:** `bbox=None`, `confidence=None`, label from decision 2, `nguon_ai='gemini'`.
5. **Detector-only boxes:** kept when the label is in `FURNITURE` (couch, chair, bed, dining table, tv, refrigerator, oven, sink, toilet, bench) and confidence ≥ 0.5. Name from `VI_TRANSLATIONS`, anchor = box centre, `nguon_ai='yolo'`.
6. **Order:** merged, then AI-only, then detector-only; within each group, larger box first (AI-only items in the order Gemini listed them). Keep 6.

`DetectedFurniture.bbox` and `confidence` become `Optional`. `processor.process_image` calls `propose` after classification and saves the result. `counts_by_category` keeps the raw detector counts used as evidence.

**4. Re-run: `python rebuild_hotspots.py [--dry-run] [--limit N]`.**
- **Selects** drafts where no object has `nguon_tao='thu_cong'`, no object has `mon_do_id`, and `review_log` has no `hotspots` action for the photo.
- **Gets items:** calls `MultimodalClassifier.classify` with the stored palette and detections, reads only `items`, and never changes the photo's labels (`relabel.py` does that).
- **Re-detects nothing:** today's stored objects are the input boxes, so `propose(stored_ai_objects, items)` runs without the GPU.
- **Writes** the new hotspots and a `review_log` row `rebuild_hotspots` holding the previous objects, one photo per transaction. A failed call leaves that photo unchanged.

Prints a summary: photos changed, points before → after, failures.

## Risks / Trade-offs

- **Gemini's point can be slightly off or name the wrong item.** → It must land inside a compatible box to merge, staff still review drafts, and points can be dragged.
- **A capped photo may lose a point staff wanted.** → They add it by hand: the editor allows up to 30.
- **The re-run costs about one call per untouched draft** (~112 today). → Dry run first; `--limit` to try a few.
- **Gemini-only points have no box,** so the editor's "AI" points without a box look like hand-made ones apart from their origin. → Origin stays `ai`, and the review log tells them apart.
- **The prompt gets longer** for every upload: a modest token increase, no extra request.

## Migration Plan

1. Deploy. New uploads get the new hotspots, and existing photos are unchanged.
2. `docker compose exec backend python rebuild_hotspots.py --dry-run`, then run it, optionally with `--limit 10` first.

**Rollback:** revert the code. Previous hotspots of rebuilt drafts are in `review_log` (`rebuild_hotspots`), and the script can restore them with `--restore`.
