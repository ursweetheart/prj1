# Proposal

## Why

seq-1 ("Gán nhãn tự động") draws the labelling workflow like this:
- the architect uploads a batch;
- the server stores the originals, queues one processing task per photo, and answers at once with each photo's id and "đang xử lý";
- a queue worker runs the AI and the embeddings for each photo, and then reports that processing is done;
- the architect sees the proposed labels **with their confidence**, confirms or corrects them, and every corrected label is recorded to evaluate the model.

Today the upload is synchronous: one request per photo, each waiting for the AI. Only the style has a confidence, and the review page never shows it. Corrections are only discoverable by digging through the general review log. The team decided the code must match the diagram.

## What Changes

- **Batch upload with a processing queue (seq-1 steps 1-6, 16):**
  - `POST /spaces/ingest` takes all the photos of an upload in one request, stores the originals and queues one task per photo;
  - it answers at once with each task's id and the status "đang xử lý";
  - a single worker processes the queue in order (steps 7-15). The queue is stored in the database, so it survives restarts;
  - the review page follows the queue, shows progress, and announces when processing is done (or which photos failed).

  **BREAKING:** the ingest response becomes a list of queued tasks, not the finished space.
- **Labels with confidence (steps 11, 17):**
  - the AI also returns a confidence for the room type;
  - both confidences are stored with the labels the AI proposed;
  - the review page shows the AI's proposal and confidence beside each label, and highlights low confidence.
- **Corrections recorded for model evaluation (steps 20-21):**
  - when a reviewer saves a room type or style different from the AI's proposal, a correction record is written (photo, dimension, AI value, confidence, correct value, who, when), and the AI's own proposal is kept unchanged on the photo;
  - `eval_labels.py` measures accuracy from these records, adding accuracy by confidence band.

## Capabilities

### New Capabilities
- `photo-intake`: batch upload into a processing queue, queue status and the "done" notice on the review page.
- `label-evaluation`: AI labels kept with confidence, shown to the reviewer, corrections recorded, and accuracy measured from them.

### Modified Capabilities
(none)

## Impact

- **Backend:**
  - `api.py`: ingest becomes batch and queued, plus a job-status endpoint, a worker started in the lifespan, and a correction hook in `PATCH /spaces/{id}`;
  - `pipeline/multimodal_classifier.py` + `schemas.py`: `space_type_confidence`;
  - `pipeline/store.py`: stores the AI labels and both confidences;
  - `pipeline/value_suggest.py`: accepting or mapping updates the corrections;
  - `relabel.py`: also refreshes the AI labels of drafts;
  - `eval_labels.py`;
  - `schema.sql`: `hang_doi_tac_vu`, `nhan_bi_sua`, new `space` columns, backfill.
- **Frontend:**
  - `src/api.js`: `uploadAll` sends one batch and polls the jobs;
  - `ReviewView.vue`: progress from the queue, the done notice, AI proposal and confidence on each card.
- **Not changed:** `sync_projects.py --ingest` keeps processing directly; it is an operator batch tool, not the architect's upload in seq-1.
