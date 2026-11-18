# Design

## Context

- **The assistant.** `pipeline/assistant.py::respond()` answers from the knowledge base (`kb_chunk`, status `dang_dung`), or else from photo descriptions through Gemini.
  - The fixed regex `FORBIDDEN` (money and promises) runs only on photo answers.
  - An unanswered question gives `FALLBACK`, a handoff lead and a row in `khoang_trong_tri_thuc`.
  - `/chat` stores each turn with `conversations.add_turn()`, which counts the unanswered ones in `hoi_thoai.chua_tra_loi`.
- **Hotspots.** They live in `space.hotspots.objects`. `with_services()` adds `service` (a `kb_chunk` title) from `SERVICE_BY_LABEL` by COCO label, and `hotspotsOf()` in `src/api.js` maps it to `kind`. The visitor card (`HotspotImage.vue`, last changed by Tùng in `b6c469b`) deliberately shows only the name, so `kind` is never drawn.
  - Items live in `mon_do`, and a hotspot links to one by `mon_do_id`.
  - `load_kb()` upserts by title, so a `kb_chunk.id` stays the same when the file is loaded again.
- **Serving.** nginx serves the SPA under `/prj1/` and proxies `/api/` to the backend. The public site address is `D3_FRONTEND_URL` (`http://localhost:8080/prj1/` in compose).
- **Projects.** The project page slug is the photo folder with `_` turned into `-`. This is the same mapping `GET /projects/{folder}/spaces` and the Lightbox link use.

## Goals / Non-Goals

**Goals:**
- One shared check that every answer passes, whichever source it came from.
- A sitemap that can never fall behind the review state.
- Services on items without a second copy of the service list.

**Non-Goals:**
- Topic detection by meaning (embeddings or an LLM). Keywords are predictable, testable and explainable to staff.
- A sitemap index, image sitemaps, `hreflang`, or pinging search engines.
- Server-side rendering or schema.org markup (the rest of roadmap 4.5).
- Listing static projects from `src/data/projects.js`. That file is Tùng's, the backend cannot read it, and "one source of project data" (0.1) is his.
- Drawing the service on the visitor's card. That would reverse Tùng's name-only change, so it is left to him; this change only makes the data right.

## Decisions

### 1. Forbidden topics are keywords, matched folded on word boundaries
- **The table.** `chu_de_cam` has these columns:
  - `id`, `ten`;
  - `ten_khoa` (folded, unique);
  - `tu_khoa text[]`;
  - `ghi_chu`, `bat`;
  - `tao_boi`, `cap_nhat_boi`, timestamps.
- **The new module.** `pipeline/topic_guard.py` holds:
  - `check(conn, text) -> {id, ten, tu_khoa} | None`, which folds the text with `taxonomy.fold`, turns `-` into a space, and matches `\b<keyword>\b` on the folded keyword;
  - no cache: one small query per chat turn, so every backend worker sees an edit at once;
  - CRUD helpers in the style of `items.py`.
- **Why.** Folding is how the rest of the assistant reads visitors, so "cong ty khac" works. Word boundaries keep "thuế" from matching inside "thiết kế".
- **Alternative rejected:** an embedding similarity threshold. It needs calibration data we lack, and its misses cannot be explained to staff.

### 2. Where the check runs in `respond()`
- **On the question:** first, before retrieval. A hit skips the knowledge-base and photo work entirely, and no Gemini call is made.
- **On the answer:** after the answer is chosen, from the knowledge base or from photos, and before the price and appointment suffixes are added. Those suffixes are our own text.
- **On a hit:**
  - `answer = FALLBACK`, `sources = []`, `images = []`, `answered = False`;
  - `out["chu_de_cam"] = {id, ten, o: "cau_hoi" | "tra_loi"}`, which `/chat` strips before replying;
  - the handoff lead is created through the existing `intent = "handoff"` path;
  - `_log_gap` is skipped.
- **The fixed `FORBIDDEN` regex** stays where it is, for photo answers.
- **Alternative rejected:** checking only the draft (the literal reading of step 15). A question about a competitor can get a harmless knowledge-base answer that still engages with the topic, so checking the question as well is cheap and safer.

### 3. Recording the hit on the message
- **Storage.** `ALTER TABLE tin_nhan ADD COLUMN chu_de_cam jsonb`. `add_turn()` takes `chu_de_cam=None`.
  - The name is stored as a copy, not a foreign key, so renaming or deleting a topic does not rewrite history.
  - No phone or email is stored here: the name and the field come from staff data.
- **Who sees it.** `_messages(staff=True)` returns it; the visitor read (`staff=False`) never does.
- **The staff view.**
  - `ConversationsView.vue` shows "Chặn: <ten> (câu hỏi|câu trả lời)".
  - It hides "Soạn đáp án" for that question. The knowledge base is not missing an answer; the topic is off-limits.
- **The list filter.** The hit counts in `chua_tra_loi`, because `answered` is false, so "Chưa trả lời được" includes it with no change to the filter.

### 4. Topic API and UI
- **Endpoints:**
  - `GET/POST /forbidden-topics` and `PATCH /forbidden-topics/{id}`, for `content` plus approvers;
  - `DELETE /forbidden-topics/{id}`, for approvers only;
  - `POST /forbidden-topics/try {text}`, which runs `check()` and returns the hit. This is staff-only and reveals nothing new to them.
- **Responses:** 409 for a duplicate name, and 422 with `{field, msg}` for validation errors.
- **The UI.** `KnowledgeView.vue` gains a third tab, "Chủ đề cấm", in the same style as the existing tabs. Keywords are entered one per line in a textarea.
- **Seed data.** No topics are created by the code. The demo can add "Đối thủ" by hand.

### 5. Sitemap from the database on each request
- **The endpoint.** `GET /sitemap.xml` in `api.py`, built with `xml.sax.saxutils.escape` and string joins. No library is needed.
  - **Base address:** `D3_FRONTEND_URL`, with a trailing slash. If it is unset, the base comes from the request's `Host` header plus `/prj1/`.
  - **Photos:** `SELECT id, relative_path, <last change>` for published spaces. The last change is the latest `review_log.at` for the space; `space` has no timestamp of its own, so a photo with no log entry gets today.
  - **Projects:** grouped from the photos by the first path segment (only those that have one), with `_` turned into `-`.
  - **Header:** `Cache-Control: public, max-age=300`.
- **Serving.** nginx gets `location = /prj1/sitemap.xml { proxy_pass http://backend:8001/sitemap.xml; }`.
- **Why on each request.** Step 18 says "update the sitemap on publish". Generating on read covers publish, take-down, return and internal moves with no hooks to forget. A few hundred rows cost nothing.
- **Alternatives rejected:**
  - a file regenerated on each status change, which means four or more call sites and a stale file if one is missed;
  - a Vite build plugin, which would be stale between deploys and would touch `vite.config.js`, a file Tùng also edits.

### 6. robots.txt
- **The file.** A static `public/robots.txt` is served by Vite and nginx at `/prj1/robots.txt`. It contains `Disallow: /prj1/quan-tri`, the other private paths, and `Sitemap: <absolute address>`.
- **Root vs. base.** Crawlers read robots.txt only from the host root. nginx therefore also gets `location = /robots.txt { alias …/prj1/robots.txt; }`.
- **The fixed address.** The `Sitemap:` line in a static file cannot follow `D3_FRONTEND_URL`. It holds the local address, with a comment saying to change it when deploying.
- **Alternative rejected:** serving robots.txt from the backend, which is more moving parts for a file that changes once.

### 7. Item → service is a foreign key to `kb_chunk`
- **The column.** `ALTER TABLE mon_do ADD COLUMN dich_vu_id int REFERENCES kb_chunk(id) ON DELETE SET NULL`.
- **Validation.** `items.py` adds `dich_vu_id` to the editable fields and checks that the id exists with `kind = 'service'`; otherwise it raises `Invalid(field="dich_vu_id")`, giving a 422.
- **Responses.** Items come back with `dich_vu_id` and `dich_vu` (the title) for staff.
- **`with_services(hotspots)` gains one query:**
  - It collects the `mon_do_id`s present.
  - It reads `mon_do.id → kb_chunk.title`, keeping only chunks where `kind = 'service' AND trang_thai = 'dang_dung'`.
  - It sets `o["service"] = item_service or SERVICE_BY_LABEL.get(label)`.
  - It takes an optional `conn`, so the two call sites (`GET /spaces/{id}`, `PUT /spaces/{id}/hotspots`) reuse theirs.
- **Pickers.** `ItemsView.vue` and the item form in `HotspotEditor.vue` get a `<select>` of service entries. The entries come from a new `GET /items/services` (STAFF), which returns `{id, title, trang_thai}` of the `kind = 'service'` entries. The knowledge endpoints are closed to architects, who edit hotspots. The first option is "Không gắn dịch vụ", and an entry not in use is labelled "(chưa dùng)".
- **Alternatives rejected:**
  - storing the service title as text on the item, which would break on a rename;
  - a link table, since one item has at most one service.

## Risks / Trade-offs

- **[Keyword lists over-block]** A broad keyword such as "giá" would silence the price answers. → The "Thử câu" box lets staff test a keyword before saving, the hit is visible per conversation, and topics can be switched off.
- **[A hit reads as "not known" to the visitor]** That is deliberate: it reveals no topic. → Staff see the real reason in the conversation detail.
- **[The sitemap lists project slugs that have no static project page yet]** A DB folder may have no entry in `projects.js`. → Accepted until 0.1 (one data source) lands. Such a page already shows its photos through `/projects/{folder}/spaces`. Noted for the fixing phase.
- **[robots.txt has a fixed host]** → A comment in the file, plus a line in `TONG-QUAN-DU-AN.md` for deployment.
- **[A service entry's kind is changed from service to faq after linking]** → The visitor sees no service, because the read filters on kind. No cascade is needed.

## Migration Plan

- **Rollout:**
  - All schema changes are additive (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) and are re-run with the usual `schema.sql` apply.
  - Rebuild the backend, then rebuild the web image for the nginx and robots.txt changes.
- **Rollback:** revert the commit. The new table and columns can stay, because nothing else reads them.
