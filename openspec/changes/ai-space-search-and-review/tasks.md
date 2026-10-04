## 1. Vector store (space-vector-store)

- [x] 1.1 Add `docker-compose.yml` with `pgvector/pgvector:pg16` and `schema.sql` mounted into initdb
- [x] 1.2 Keep the embedding in `SpaceRecord` and return it from `processor.py` (single and directory paths)
- [x] 1.3 Add `pipeline/store.py` upsert that preserves `review_status` on re-ingest
- [x] 1.4 Add `ingest.py` and ingest the 152 images of `image_d3/` (152 rows, all with embeddings)
- [x] 1.5 Add `reembed.py` to resize the column and recompute vectors without Gemini calls

## 2. Embedder (image-feature-extraction)

- [x] 2.1 Benchmark ViT-B/32, ViT-L/14, SigLIP2 B/16 and SO400M on the stored images (neighbour accuracy, Vietnamese P@5, VRAM)
- [x] 2.2 Switch `VisionEmbedder` default to SigLIP2 ViT-B/16 (768-d) and add `embed_text`
- [x] 2.3 Evaluate a local VLM (Qwen2.5-VL-3B, 4-bit) as a Gemini replacement; rejected (6/20 space-type agreement)
- [x] 2.4 Remove the random-vector fallback in `VisionEmbedder` so a failed model load fails ingest (compiles; ingest not re-run, Docker down)

## 3. Similarity search (space-similarity-search)

- [x] 3.1 Add `pipeline/search.py` with `similar_to` (same space type, excludes self, `[]` for unknown path) and `by_text`
- [x] 3.2 Return the space id with each hit
- [x] 3.3 Add `tests/test_search.py` (self-exclusion/type filter, Vietnamese text with filter)
- [x] 3.4 Cap `k` inside `search.py` (`MAX_K`) and cache the embedder so text search no longer reloads the model per query (tests not run, Docker down)

## 4. API (space-review-api)

- [x] 4.1 Add `api.py` with `GET /spaces`, `GET /spaces/{id}`, `GET /spaces/{id}/similar`, `GET /search`
- [x] 4.2 Add `POST /spaces/ingest` with extension check, base-name sanitising and `/images` static mount
- [x] 4.3 Add `PATCH /spaces/{id}` with taxonomy validation and the ordered review state machine
- [x] 4.4 Add `tests/test_api.py` (filter, similar, Vietnamese search, review flow) and a manual ingest check
- [x] 4.5 Add tests for ingest rejection (415) and the 409 final-state case so they run without Gemini (written; not run, Docker down)

## 5. Prototype UI (space-discovery-ui)

- [x] 5.1 Add Vite proxy for `/api` and `/images`, and `src/api.js` mapping DB values to prototype facet ids
- [x] 5.2 Add text search box with error and clear handling on `CongTrinhView.vue`
- [x] 5.3 Add `SpaceView.vue` at `/khong-gian/:id` with caption, materials, palette and "Dự án tương tự"; add route; give `SpaceCard` an `href` prop
- [x] 5.4 `vite build` passes
- [x] 5.5 Verify in a browser against the live API: search, open a result, follow a similar space, unknown id, API down (all five checked; note `/cong-trinh` without trailing slash serves the old static cong-trinh.html in dev)
- [ ] 5.6 Commit the prototype changes. `prototype/` is its own git repo (branch `Tuan`); the commit currently sits on its `master` and must be moved to `Tuan`. No `.gitignore` needed: `dist/` is tracked there

## 6. Access control (follow-up; protects space-review-api)

- [x] 6.1 Approach: own accounts (email + argon2 password, JWT bearer, 60 min) plus Google OIDC; roles visitor, architect, content, sales, lead_architect, admin; self sign-up yields visitor, admin grants roles (`set_role.py`)
- [x] 6.2 User registration and login with hashed passwords and token/session issuance
- [x] 6.3 Google sign-in (authorization-code + OIDC) with account linking by verified email; linking clears the password. Needs GOOGLE_CLIENT_ID/SECRET: linking logic tested, live redirect not tested
- [x] 6.4 Authorization: only architect roles may ingest and edit facets; approval/publish limited to lead architect; anonymous visitors see only `published` spaces
- [x] 6.5 Audit log of review actions (who changed what, when)
- [x] 6.6 Tests for each role against each protected endpoint

## 7. Remainder of the week (RAG assistant, seq-3)

- [ ] 7.1 Knowledge base: ingest project descriptions, price list and FAQ, chunk and embed
- [ ] 7.2 Chat endpoint: extract request (project type, area, style, price intent), hybrid retrieval, grounded answer with sources and three project images
- [ ] 7.3 Anti-hallucination threshold: below it, answer that the information is missing and hand off to an architect
- [ ] 7.4 Lead handoff: create a lead with the conversation when price or appointment intent is detected
- [ ] 7.5 Hotspot "item → service" from `furniture_detection`
- [ ] 7.6 Evaluation set (about 30 images/questions): facet accuracy against NFR-10 (≥85%), cost per image, run guide

