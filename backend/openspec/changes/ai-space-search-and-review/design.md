## Context

The pipeline in `pipeline/` (color, YOLO furniture, embedder, Gemini classifier) produced records that were only written to CSV/JSON, and the embedding was reduced to its length. The website prototype (`prototype/`, Vue 3 + Vite) runs on static mock data. Diagrams seq-1/2/3 separate "Cơ sở dữ liệu" from "Chỉ mục vector", but at the current scale (152 images, target up to a few thousand) one database is enough. Hardware is a 4 GB RTX 3050 laptop GPU.

Measurements on the 152 ingested images drove the model decisions:

| Embedder | 1-NN same folder | Vietnamese P@5 | Peak VRAM |
|---|---|---|---|
| ViT-B/32 (old) | 0.89 | 0.45 | 0.57 GB |
| ViT-L/14 | 0.93 | 0.30 | 1.6 GB |
| SigLIP2 B/16 | 0.93 | 0.95 | 1.6 GB |
| SigLIP2 SO400M | 0.95 | 0.95 | 4.29 GB (exceeds GPU) |

A local VLM (Qwen2.5-VL-3B, 4-bit, 2.55 GB, 6.6 s/image) matched Gemini on space type for only 6 of 20 images.

## Goals / Non-Goals

**Goals:**
- Persist spaces and embeddings, search by image and by Vietnamese text, filter by facet in SQL.
- Expose it over HTTP with a human-in-the-loop review workflow and show it in the prototype.
- Reproducible setup from the repo (`docker compose up`, `schema.sql`).

**Non-Goals:**
- Authentication, authorization, OAuth, user accounts (follow-up; see Risks).
- RAG assistant, lead handoff, behaviour tracking and trend dashboards.
- ANN indexes (HNSW/IVFFlat) and horizontal scaling.
- Replacing Gemini with a local model.

## Decisions

- **Postgres + pgvector over SQLite+numpy or Chroma.** Hybrid queries (`WHERE space_type = … ORDER BY embedding <=> $1`) are one SQL statement, and leads, conversations and review state are relational anyway. Alternatives: SQLite+`.npy` (no extra service, but filtering and future tables are hand-rolled), Chroma (extra store to keep in sync).
- **SigLIP2 ViT-B/16 (768-d) as the embedder.** Best Vietnamese retrieval that fits 4 GB. SO400M is marginally better but does not fit; ViT-L/14 is worse for Vietnamese. Text queries need no translation.
- **Unit of labelling is `Space`, not project.** One row per image (`relative_path` unique, e.g. `modern/behance_img_1.jpg`), matching the taxonomy decision in the requirements analysis.
- **Image similarity is restricted to the same `space_type`** (a bedroom never returns a kitchen); text search takes an optional `space_type` filter. Score is cosine similarity (`1 - distance`).
- **Re-ingest keeps review decisions.** The upsert never overwrites `review_status`, so architect work survives re-classification. `reembed.py` updates only the vector column and does not call Gemini.
- **Review workflow is a strict linear state machine** `draft → in_review → approved → published`, advanced one step per request under `SELECT … FOR UPDATE`; facet edits are validated against the schema's allowed values. AI never publishes by itself.
- **Ingest is synchronous.** One GPU, about 10 s per image; bulk loads use `ingest.py`. A queue is deferred until volume requires it.
- **Models load lazily** inside the API process (processor on first ingest, embedder on first text search) so read-only endpoints start fast.
- **Frontend talks to the API through a Vite proxy** (`/api` → `:8000`, `/images` → `:8000`), avoiding CORS in development. `src/api.js` maps DB values (`phong_khach`, `Hien_dai`) to the prototype's facet ids so existing labels and `SpaceCard` are reused; the mock facet filter is left untouched.
- **Detail page is new** (`/khong-gian/:id`) because the prototype's old link target did not exist.

## Risks / Trade-offs

- [Endpoints are unauthenticated: anyone reaching the API can ingest or change review state] → Local development only; auth follow-up (register, login, OAuth, roles) must land before any network exposure.
- [Changing the embedder invalidates stored vectors and the column dimension] → `reembed.py` alters the column and recomputes without Gemini cost; document dimension in `schema.sql`.
- [Gemini labels are unreviewed and skewed (62 of 152 "Luxury", 5 "Japandi")] → Review workflow plus adding more images; accuracy measured against NFR-10 (≥85%) in the evaluation task.
- [`VisionEmbedder` silently falls back to a random vector if the model fails to load] → Known hazard; treat a load warning as a failure when ingesting, remove the fallback in a later cleanup.
- [Docker Desktop on the dev laptop can stall after being force-killed] → Stop with `docker compose stop`, never kill Docker Desktop processes.
- [Synchronous ingest blocks one worker for about 10 s] → Acceptable at this scale; revisit with a job queue.
- [Brute-force vector scan] → Fine below ~10k rows; add HNSW beyond that.

## Migration Plan

1. `docker compose up -d` (creates `space` from `schema.sql` on a fresh volume).
2. `python ingest.py image_d3` to classify and store images (about $0.05 for 152 images).
3. Existing databases built with a different embedder: run `python reembed.py`.
4. Rollback: the table is additive; drop `space` or point `D3_DSN` elsewhere. The CSV/JSON outputs in `outputs/` are untouched.

## Open Questions

- Which text embedding model serves the RAG knowledge base (SigLIP2 text tower vs a dedicated text model)?
- Auth provider and roles for the follow-up (own accounts, Google OAuth, or both)?
- Whether published spaces should be the only ones visible to anonymous visitors once auth exists.
