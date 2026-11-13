## Context

Today the taxonomy is expressed as Python `Literal` enums (`pipeline/schemas.py`) and static synonym dicts (`pipeline/assistant.py`). A runtime cannot add a value to a `Literal`, so neither UC15 (manage taxonomy) nor automatic discovery is possible without first making the taxonomy data-driven.

The goal here is the hardest discovery tier: finding a **new dimension (chiều)** — a whole new classification axis — rather than a new value inside an existing dimension, or a synonym of an existing value. A genuine new dimension is an axis along which content varies that the current taxonomy does not already capture, and that recurs across existing facet values (living rooms, bedrooms, kitchens can all sit anywhere along it).

**Method: no model training — API analysis + scoring.** Consistent with how the rest of the repo already works (zero-shot classification in `multimodal_classifier`, benchmark scoring in `eval_labels.py` / `eval_assistant.py`), discovery never trains a model. It calls Gemini to *analyze* the existing material and *propose* candidate dimensions, and it attaches an **evidence score** to each proposal. The operational flow is the same as the convergence design — **sources → candidate proposals → scoring / convergence → human gate → rollout** — only the mechanism inside each stage is a Gemini call plus a score, not embedding math and nothing trained. This keeps spend bounded (an occasional batch job) and leaves durable outputs (proposals, tags) in the database that remain usable after API credit lapses.

We still require **multi-source convergence**: a candidate is trusted more when images, conversations, and behavior independently raise it. Today only the **image source has data** (~160 photos in `image_d3`); chat and behavior logs barely exist yet, so the realistic v1 is image-source discovery via Gemini, review-gated, with the other sources raising scores once the site has traffic.

## Goals / Non-Goals

**Goals:**
- Make the taxonomy database-backed: `ChieuPhanLoai`, `GiaTriPhanLoai` (with `tu_dong_nghia`, stable `ma_dinh_danh`), `UngVienPhanLoai` for staged proposals.
- Propose dimension candidates by calling Gemini to analyze each source, representing every candidate uniformly as a **scored proposal** so sources are comparable.
- Promote a candidate only above an evidence-score threshold (raised by multi-source support), stage it for human review; never auto-apply.
- On human acceptance, create the dimension, back-tag the whole library (Gemini tags each space along it), and generate the filter + SEO URLs.
- Collect behavior only with recorded consent (`da_dong_y_thu_thap`, act-7, NFR-09, NĐ13/2023).

**Non-Goals:**
- Training any model: discovery reuses zero-shot API analysis + scoring, never a trained model.
- Auto-*applying* any taxonomy change without human approval (contradicts M9 / seq-15; explicit non-goal).
- Discovering new *values* within an existing dimension, or learning *synonyms* — the same data model and emitters support these, but the discovery logic here targets dimensions only; value/synonym suggestion is a later change.
- Fully automated naming: Gemini proposes a name, a human confirms it.
- Deleting dimensions (dimensions are near-permanent because they become URL/SEO structure; values may be merged).

## Decisions

- **D1 — Taxonomy as data, stable ids.** Dimensions/values are rows with an immutable `ma_dinh_danh` separate from the display `ten`. Renames change `ten` only; merges migrate all labels to the target id then delete the source (seq-15 b13/b19). This keeps facet URLs (NFR-07) stable across edits. The hardcoded `parse_request` dicts become seed rows in `tu_dong_nghia`.
- **D2 — No training; Gemini analysis + scoring.** Discovery is a batch job that calls Gemini to analyze content and return structured proposals, each with a score — the same zero-shot + eval pattern the repo already uses. There is no training step and no model to retrain.
- **D3 — Gemini proposes dimensions, not embedding math.** Feed Gemini a capped sample of the existing per-space material (captions / transcripts, and/or sample images) together with the *current* taxonomy, and ask it to propose classification **dimensions** that are (a) absent from the current taxonomy and (b) orthogonal to it (values should spread across existing dimensions). Output is structured: dimension name, candidate values, example space ids, a self-reported confidence. Gemini is instructed to ignore photographic/capture artifacts (angle, lighting, which scrape/photographer).
- **D4 — Evidence score; convergence = sources agree.** Each candidate carries an evidence score combining **coverage** (how many spaces it cleanly labels), **distinctness** (not a rephrasing of an existing dimension), and **demand** (chat / behavior mentions, when available). Independent support from a second source raises the score — that is what "convergence" means in the scoring model. Promote candidates above a score threshold; keep the rest as low-score / pending.
- **D5 — Distinctness & nameability are Gemini checks.** Ask Gemini to confirm the proposal is not already expressible via existing dimensions/values and that each value is nameable with a short Vietnamese phrase; non-distinct or un-nameable proposals are down-scored, not promoted.
- **D6 — Human-in-the-loop + rollout.** Top-scored candidates become `UngVienPhanLoai` rows marked `[AI SINH - CHƯA DUYỆT]` (the marker convention already used for unreviewed KB text). KTS trưởng reviews name, value labels, example images, and the score breakdown. Acceptance creates the `ChieuPhanLoai`, back-tags the library (Gemini tags each space along the new dimension; low-confidence tags flagged per QT01 "đủ features bắt buộc"), and emits filter + SEO URLs.
- **D7 — Batch & bounded (credit-aware).** Discovery runs as an occasional offline batch with caps on sample size and number of API calls; its outputs (proposals, tags) persist in the database and remain usable after API credit lapses. Score thresholds and the sample/call caps are configuration with sane defaults, calibrated on real data — not fixed constants.

## Risks / Trade-offs

- **[Risk] The LLM invents plausible-but-useless dimensions.** Mitigation: score by coverage + distinctness, require a demand signal for a high score, and always gate on a human; bounded batch runs cap the blast radius.
- **[Risk] Capture/scrape confound.** The library is Behance scrapes grouped by folder, so Gemini might propose "photographer / render style". Mitigation: instruct Gemini to ignore capture artifacts, and the human gate catches the rest.
- **[Risk] Bootstrap dependency.** Convergence wants behavior and chat-gap signals, which barely exist today. Mitigation: v1 runs on the image source alone; the other sources raise scores once traffic exists (by design, not a bug).
- **[Risk] Dimensions are near-permanent** (URL/SEO). Mitigation: high score bar, propose rarely, human gate, merge-not-delete.
- **[Trade-off] Cost of acceptance.** Creating a dimension re-tags the whole library via Gemini. Accepted as the price of a real new facet; runs as a background batch (seq-15 b20 already models an index-update queue).
- **[Risk] Credit window.** API credit is limited and time-boxed. Mitigation: discovery is batch, not per-request; cap calls per run; persist all outputs so value survives credit expiry (D7).
- **[Risk] Privacy.** Behavior collection without consent breaches NFR-09 / NĐ13/2023. Mitigation: gate every event on `da_dong_y_thu_thap`; keep only anonymous aggregates otherwise (act-3 b8).
