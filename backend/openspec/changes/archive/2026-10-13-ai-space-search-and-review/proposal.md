## Why

The preprocessing pipeline classifies each interior image (color, furniture, Gemini facets) but throws the embedding away and keeps results only in CSV/JSON, so nothing can be searched, reviewed or shown on the website. The sequence diagrams seq-1 (auto-tagging), seq-2 (similar spaces) and seq-3 (RAG assistant) all need a persistent store with vector search first; the goal is a working AI flow within the week.

## What Changes

- Persist every `Space` record with its image embedding in Postgres + pgvector (`space` table, `schema.sql`, Docker Compose).
- Switch the embedder from OpenCLIP ViT-B/32 (512-d) to SigLIP2 ViT-B/16 (768-d): Vietnamese text queries reach P@5 0.95 vs 0.45 on the 152-image set. **BREAKING**: stored vectors must be recomputed (`reembed.py`) when the embedder changes.
- Similarity search by image and by Vietnamese text, always restricted to the same space type for image queries.
- FastAPI service: list/get spaces, similar spaces, text search, image ingest, and a review workflow `draft → in_review → approved → published` with architect edits to facets (QT-01, human-in-the-loop).
- Prototype website: text search box on the portfolio page and a space detail page with a "Dự án tương tự" block, both backed by the API.
- Authentication/authorization (register, login, OAuth, roles) is planned as a follow-up so the review and ingest endpoints are not open; it is listed but not implemented here.
- RAG assistant (seq-3) and lead handoff are planned remainder, specified only at task level.

## Capabilities

### New Capabilities
- `space-vector-store`: Postgres/pgvector persistence of space records, facets, palette, hotspots, review status and embeddings; re-embedding without re-classifying.
- `space-similarity-search`: nearest-space search by image and by natural-language (Vietnamese) text, with space-type filtering and similarity scores.
- `space-review-api`: HTTP API for listing, reading, ingesting and reviewing spaces with an ordered review-state workflow.
- `space-discovery-ui`: prototype pages that expose text search and similar-space suggestions from the API.

### Modified Capabilities
- `image-feature-extraction`: embedding model becomes SigLIP2 ViT-B/16 producing 768-dimensional normalized vectors, and the vector is persisted rather than only measured.

## Impact

- Code: `pipeline/` (`vision_embedder.py`, `processor.py`, `schemas.py`, new `store.py`, `search.py`), root `api.py`, `ingest.py`, `reembed.py`, `schema.sql`, `docker-compose.yml`, `tests/`, `prototype/src` (`api.js`, `SpaceView.vue`, `CongTrinhView.vue`, `SpaceCard.vue`, router, `vite.config.js`).
- Dependencies: `psycopg[binary]`, `pgvector`, `fastapi`, `uvicorn`, `python-multipart`, `httpx`, `pytest`; Docker for Postgres.
- Runtime: one 4 GB GPU shared by YOLO and the embedder (about 1.6 GB for SigLIP2); Gemini remains the classifier (about $0.0003 per image).
- Security: ingest and review endpoints are unauthenticated until the auth follow-up lands.
