# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.

Tests create throw-away entries titled `test_kn_*` and throw-away questions, removed afterwards. The live sample entries are not changed.

## 1. Data and loading

- [x] 1.1 Make these idempotent changes in `backend/schema.sql`, then re-apply it:
  - `kb_chunk` adds `cum_tu_khop`, `trang_thai` (CHECK; default `dang_dung`), `nguon`, `tu_cau_hoi int[]`, `updated_at` and `updated_by`;
  - backfill `cum_tu_khop` from the title, and set `nguon` from the markers;
  - `khoang_trong_tri_thuc` adds `trang_thai` (default `mo`) and `kb_chunk_id`;
  - a new table `nhat_ky_tri_thuc`.

  In `assistant.retrieve`, keep only `dang_dung` entries. In `assistant.load_kb`, store `cum_tu_khop`, store AI-marked entries as `cho_duyet` / `nguon='ai'`, and never overwrite the status of an existing row. Re-load `kb/sample.json` and load `kb/generated.json`.

  Verify with tests in `tests/test_knowledge.py`:
  - an entry set to `tat` is not returned by `retrieve`;
  - loading a file with an AI-marked entry stores it as `cho_duyet` and `retrieve` skips it;
  - re-loading a live entry keeps it live, and re-loading a draft keeps it a draft;
  - `tests/test_assistant.py` still passes.

  After loading, the database holds 11 `dang_dung` entries and 8 `cho_duyet` entries.

## 2. Rules and API

- [x] 2.1 Create `backend/pipeline/knowledge.py` with:
  - `needs_price_approval` (the money regex);
  - `create`, `update` (re-embedding the title and match phrases; a content edit of a live price entry goes to `cho_duyet`);
  - `set_status` (the move table, the price rule, stripping the AI marker, closing linked questions);
  - `delete`;
  - the protection of hotspot-linked titles;
  - `gaps` (grouped by the folded question) and `dismiss_gap`;
  - a log row per write.

  Verify with unit tests:
  - the regex flags "250.000 đ/m²", "1,5 tỷ", "từ 300 triệu" and "45tr", and does not flag "3 đến 4 tuần" or "24 tháng";
  - content switching on a price entry raises the 403 error, and an approver can;
  - a content edit of a live price entry's answer makes it `cho_duyet`, while a title-only edit stays live;
  - switching an AI draft on strips its marker;
  - an edit re-embeds, so `retrieve("<new match phrase>")` ranks it first;
  - renaming or deleting "Dịch vụ thiết kế phòng khách" is refused, while editing its text works;
  - "Có làm văn phòng không?" and "co lam van phong khong" form one group of 2;
  - switching on an entry made from a group closes those rows with `kb_chunk_id`;
  - dismissing sets `bo_qua`;
  - each write logs one row.
- [x] 2.2 Add the `/knowledge` endpoints from design decision 7 in `backend/api.py`.

  Verify with API tests:
  - content and the lead architect get 200;
  - sales gets 403, anonymous 401;
  - DELETE by content gets 403;
  - a duplicate title gets 409;
  - a linked rename gets 409;
  - list items carry `can_duyet_gia`, `mau` and `lien_ket`;
  - after an approver switches on a test entry, `POST /chat` with a question equal to its match phrase answers with its text, and after `tat` it does not.

## 3. Frontend

- [x] 3.1 In `src/api.js`, add the knowledge calls. Create `KnowledgeView.vue` at `/quan-tri/tri-thuc` (`page-top`; the two tabs; the entries list with search, status chips and badges; the editor with role- and status-dependent buttons; errors by the fields; a delete confirmation; the questions tab with "Soạn đáp án" and "Bỏ qua"). Add the route and the "Tri thức" link in `SiteNav.vue`.

  Verify in the browser:
  - **As a content user:**
    - create a general entry and switch it on;
    - create a price entry: "Gửi duyệt" is shown instead of "Bật sử dụng", and it lands in "Chờ duyệt";
    - "Soạn đáp án" from a throw-away question group pre-fills the form, and switching the entry on removes the group;
    - "Bỏ qua" removes a group;
    - no "Xoá" button.
  - **As the lead architect:**
    - approve the price entry;
    - approve an AI draft, and its marker is gone;
    - delete a test entry after confirming.
  - **Everywhere:**
    - a linked service title shows why it cannot be renamed;
    - keyboard only works;
    - 360px has no sideways scroll;
    - the title is not under the header.

## 4. Docs

- [x] 4.1 Update `TONG-QUAN-DU-AN.md`:
  - UC16 / seq-16 status;
  - roadmap 1.5 (and the note that roadmap 1.6 can now be done in the UI);
  - the API table;
  - the tables;
  - the commands for loading `kb/*.json` with the new draft behaviour.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
