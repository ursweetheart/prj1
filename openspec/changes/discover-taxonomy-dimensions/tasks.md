## 0. Data-driven taxonomy foundation (prerequisite)

- [x] 0.1 Add `chieu_phan_loai`, `gia_tri_phan_loai`, `ung_vien_phan_loai` tables to `backend/schema.sql` (stable `ma_dinh_danh`, `tu_dong_nghia` jsonb, `bat_buoc` / `cho_phep_nhieu_gia_tri` / `hien_thi_cho_khach` / `thu_tu`). Also added `space_gia_tri` (space↔value link).
- [x] 0.2 Seed the tables from the current `Literal` values and the `parse_request` synonym dicts (`kb/taxonomy_seed.json` + idempotent `seed_taxonomy.py`; also captures the latent `loai_cong_trinh` dimension). Space↔value population happens at cutover (0.3).
- [x] 0.3 `pipeline/taxonomy.py` (DB + `kb/taxonomy_seed.json` fallback, cached); `assistant.parse_request` now reads synonyms/values from it. Kept the `schemas.py` `Literal` as the canonical seed + Gemini-output validator (the classifier normalises to it; the seed mirrors it, guarded by `test_taxonomy_seed`) instead of removing it — layering the data lookups is the smaller, safer diff for the two built-in dimensions. Cutover done: trigger `sync_ai_tags` (schema.sql) keeps `space_gia_tri` in step with the AI columns; added `tong_mau`, `vat_lieu`, `muc_dau_tu` so the portfolio filters on 6 dimensions (SG-01).
- [x] 0.4 `backend/api.py`: `GET /taxonomy` (public, for filters) + add-value / rename / merge behind `lead_architect` (UC15); merge migrates `space_gia_tri` and returns the affected count. Vector-index label refresh (seq-15 b20–22) left as a future queue job. Tested in `tests/test_taxonomy_api.py`.

## 1. Candidate emitters — Gemini analysis, no training (can run in parallel once Phase 0 lands)

- [x] 1.1 **Images** — `pipeline/discovery.py`: bounded batch job (one Gemini call, capped sample) that sends space captions/transcripts (+ the current taxonomy) and collects proposed new dimensions (name, values, example space ids, confidence); prompt ignores capture artifacts; each proposal scored (coverage + distinctness; demand term 0 until other sources exist). `--dry-run` prints, else stores to `ung_vien_phan_loai`. Scoring unit-tested in `tests/test_discovery.py`.
- [ ] 1.2 **Conversations** — in `respond()`: log a knowledge-gap record (question + folded unmapped terms + best cosine) when below `MIN_SCORE` / `MIN_TEXT_SCORE` instead of only creating a handoff lead; feed recurring gaps to the proposer as a contributing source.
- [ ] 1.3 **Behavior** — `su_kien` / `phien_truy_cap` tables + event-ingest endpoint (UC21) gated on `da_dong_y_thu_thap`; enrich events with the viewed content's facet values; use facet co-occurrence as a demand signal (QT06 b16).
- [ ] 1.4 Consent banner on the frontend (act-7, NFR-09); events dropped / anonymized without consent.

## 2. Scoring & convergence

- [ ] 2.1 Merge candidates from all sources into one proposal record per dimension; compute an evidence score = coverage + distinctness + demand.
- [ ] 2.2 Promote candidates above the score threshold; ≥2-source support boosts the score; keep the rest as pending.
- [ ] 2.3 Gemini distinctness/nameability check: down-score proposals already expressible by the current taxonomy or not nameable by a short Vietnamese phrase.
- [ ] 2.4 Expose the score threshold and the sample / API-call caps as configuration with calibrated defaults (credit-aware, D7).

## 3. Human review + rollout

- [ ] 3.1 Promoted candidates → `ung_vien_phan_loai` marked `[AI SINH - CHƯA DUYỆT]` with the score breakdown (coverage / distinctness / demand, contributing sources) and example images.
- [ ] 3.2 Taxonomy manager view (seq-15): review candidate, edit name/value labels, accept / reject.
- [ ] 3.3 On accept: create `ChieuPhanLoai`, back-tag the library by having Gemini tag each space along the new dimension (flag low-confidence per QT01 "đủ features bắt buộc"), generate filter + SEO URLs.

## 4. Verification (scoring, not training)

- [ ] 4.1 Score the discovery output: run on the current `image_d3` library, have a human mark which proposals are real, and report precision (mirrors `eval_labels.py`). Confirm capture/scrape artifacts are not among the top proposals.
- [ ] 4.2 Confirm no dimension is ever created without an accepted `ung_vien_phan_loai` row (human gate).
- [ ] 4.3 Confirm events without consent are not persisted.

## 5. Documentation (optional, low priority)

- [ ] 5.1 Add `UngVienPhanLoai` to the class diagram and the signal→scoring→gate flow to the sequence diagrams in `prj1_tailieu/project 1`.
