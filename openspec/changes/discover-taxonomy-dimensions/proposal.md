## Why

The taxonomy is the heart of the system (M1), yet today it is **hardcoded**: `space_type` and `design_style` are `Literal` enums in `pipeline/schemas.py`, and the customer-vocabulary synonyms live as static dicts in `pipeline/assistant.py` (`PROJECT_TYPES`, `STYLE_ALIASES`, …). This violates NFR-13 ("adding a style must not require a code change") and leaves UC15 (Quản lý taxonomy) unimplemented.

More importantly, the design positions the website as a **sensor** that should *discover* how customers actually think about space — including along axes nobody defined in advance (a new **dimension / chiều**, e.g. "mật độ cây xanh", not just a new value inside an existing dimension). The diagrams already produce the raw signals for this (QT06 "phát hiện nhóm thị hiếu mới", act-4 "ghi lỗ hổng tri thức", QT01 "AI đề xuất nhãn"), but the automated bridge from those signals to a proposed taxonomy change is drawn nowhere, and seq-15 (the only place dimensions/values are created) is 100% manual.

This change builds that bridge: **multi-source convergence** that proposes a brand-new taxonomy *dimension* only when independent sources (images, conversations, behavior) agree it exists and matters — and always routes the proposal to a human (KTS trưởng) for approval. We do convergence first (not image-only) to keep precision acceptable and avoid garbage axes.

## What Changes

- **Taxonomy becomes data, not code.** Dimensions, values, and synonyms move out of `Literal` enums / hardcoded dicts into database-backed `ChieuPhanLoai` / `GiaTriPhanLoai`, with stable `ma_dinh_danh` so renames/merges never break facet URLs (NFR-07). A new `UngVienPhanLoai` entity stages AI proposals awaiting review.
- **Three independent candidate emitters (via Gemini, no training).** (1) Images: a bounded batch job sends a capped sample of space captions/transcripts (+ the current taxonomy) to Gemini and collects proposed new dimensions with example spaces and a confidence. (2) Conversations: `respond()` logs knowledge gaps and unmapped customer terms (act-4 b8) instead of discarding them. (3) Behavior: consented `SuKien` / `PhienTruyCap` events (act-7) supply a demand signal from facet co-occurrence (QT06 b16).
- **Score, not pooling.** Every candidate is a uniform scored proposal; a dimension is promoted only above an evidence-score threshold (coverage + distinctness + demand), raised when **≥2 independent sources support it**, and after a Gemini distinctness/nameability check. Discovery runs as a bounded batch, so API spend is small and its outputs persist in the DB (usable after credit lapses).
- **Human gate + rollout.** Promoted candidates land in the seq-15 taxonomy manager marked `[AI SINH - CHƯA DUYỆT]`. On approval the system creates the dimension, back-tags the whole library using the residual projection, re-indexes, and generates the new filter + SEO URLs.

## Capabilities

### New Capabilities
- `taxonomy/data-driven-taxonomy`: Database-backed dimensions, values, synonyms, and candidate staging with stable identifiers; runtime add / rename / merge; replaces hardcoded enums and synonym dicts (UC15, NFR-13).
- `taxonomy/candidate-signals`: Three independent dimension-candidate emitters (image residual axes, conversation knowledge-gaps, behavior session clusters) expressed in the shared SigLIP2 embedding space.
- `taxonomy/dimension-convergence`: Cross-source alignment, multi-source agreement voting, nameability gate, human review, and library back-tagging for accepted dimensions.

### Modified Capabilities
- (none formally specified yet — classification/search behavior is affected in practice; see Impact)

## Impact

- `backend/schema.sql`: new tables `chieu_phan_loai`, `gia_tri_phan_loai`, `ung_vien_phan_loai`, `su_kien`, `phien_truy_cap`; `space` gains data-driven facet links.
- `backend/pipeline/schemas.py`: `space_type` / `design_style` `Literal`s become references to data-driven values.
- `backend/pipeline/assistant.py`: `parse_request` synonyms read from `tu_dong_nghia`; `respond()` logs knowledge gaps + unmapped terms.
- `backend/pipeline/` (new): `taxonomy.py` (model + CRUD), `discovery.py` (Gemini proposals, scoring, convergence), event ingestion.
- `backend/api.py`: taxonomy admin endpoints (UC15), event-ingest endpoint (UC21), candidate review endpoints.
- `src/`: admin taxonomy manager view (seq-15), consent banner (act-7, NFR-09), data-driven facet filter generation.
- `prj1_tailieu/project 1/Class diagram` & `Sequence diagram`: add `UngVienPhanLoai` and the signal→gate flow (documentation; separate task).
