# Proposal

## Why

The AI hotspots on photos are noisy and often land in the wrong place. Measured on the 152 photos in the database (1,229 AI points):

- **8.1 points per photo** on average; visitors see a cluttered photo.
- **369 points (30%) have confidence below 0.4.**
- **180 pairs of points overlap** on the same object with the same label (a sofa with two dots).
- Small objects crowd out furniture: chai (bottle) 78, sách (book) 45, bát (bowl) 40, cốc (cup) 30.
- **Missing items:** the detector (YOLO, COCO classes) has no class for đèn chùm / đèn (lamp), thảm (rug), tủ (cabinet, wardrobe), rèm (curtain), gương (mirror) or tranh (artwork), which are what an interior studio wants to point at.
- **Points miss the object:** the point is the centre of the detection box, which falls in empty space for chairs, L-shaped sofas or a table seen from the side.

Staff can already fix points by hand (move, add, delete; change `hotspot-items`), but every photo starting this noisy makes that a lot of work.

## What Changes

- **Gemini names and points at the main items, in the call it already makes.** At upload, the classification request also asks for up to 8 main interior items, each with a Vietnamese name, a category from a fixed list, and **a point lying on the item**. There is no extra AI call.
- **Merge with the detector:**
  - When a Gemini point falls inside a detector box, the two become one hotspot: Gemini's name and point, the detector's box, confidence and label.
  - A Gemini item with no box becomes a hotspot without a box. This covers lamps, rugs, curtains and the like.
  - A detector box with no Gemini point is kept only if it's furniture (not a small object) with confidence ≥ 0.5.
- **Clean up:**
  - Drop small objects (bottle, cup, bowl, book, glass, cutlery, remote, phone, person…).
  - Drop detector boxes below 0.4.
  - Merge points for the same object (same label, boxes overlapping by more than half).
  - **Keep at most 6 points**: matched points first, then Gemini-only points, then detector-only points; larger items first within each group.
- **Without Gemini** (no key or a failed call), the detector's boxes still get the clean-up and the cap.
- **One-off re-run for existing drafts:** a script rebuilds the AI points of **draft photos whose hotspots no person has touched** (no hand-made point, no linked item, no hotspot edit in the review log). Photos in review or published, and anything edited by hand, are left alone. It reuses the stored detections and costs one Gemini call per photo.

## Capabilities

### New Capabilities

- `hotspot-detection`: how the system proposes hotspots for a photo: sources, merging, clean-up, cap, and the re-run for untouched drafts.

### Modified Capabilities

None. `hotspot-items` (hand editing, origin, item library) is unchanged. A Gemini-only point is an AI point without a detection box, which that spec already allows for points that have no box.

## Impact

- **Backend:**
  - `pipeline/multimodal_classifier.py`: the prompt and result gain `items`.
  - `pipeline/schemas.py`: `DetectedFurniture.bbox` becomes optional, plus an optional `nguon_ai` (`yolo` | `gemini` | `ca_hai`).
  - New `pipeline/hotspots.py`: merge, clean-up and cap.
  - `pipeline/processor.py`: merges before saving.
  - New `rebuild_hotspots.py`: the one-off re-run.
- **Readers unchanged:** `hotspotsOf` in `src/api.js`, `HotspotImage.vue`, `HotspotEditor.vue` and `with_services` read `hotspot_anchor` and `label_vi`. `with_services` maps services by `label`, so Gemini categories are given detector-style labels where one exists (e.g. sofa → `couch`).
- **AI cost:**
  - At upload: a slightly longer answer from the existing call.
  - Re-run: about 112 calls for today's drafts (one per untouched draft).
- **Data:** hotspots of re-run drafts are replaced, with the old ones written to the review log.
