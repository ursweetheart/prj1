# Tasks

## 1. Forbidden topics (backend)

- [x] 1.1 Schema. Add table `chu_de_cam` to `schema.sql`, with these columns:
  - `id`, `ten`;
  - `ten_khoa` (unique);
  - `tu_khoa text[]`;
  - `ghi_chu`, `bat`;
  - `tao_boi`, `cap_nhat_boi`, timestamps.

  Also add `ALTER TABLE tin_nhan ADD COLUMN IF NOT EXISTS chu_de_cam jsonb`. Apply it to the running db.
- [x] 1.2 `pipeline/topic_guard.py`:
  - `check(conn, text)`: folded, `-` read as a space, whole-word match, switched-on topics only, uncached (one small query per turn, so every backend worker sees an edit at once);
  - CRUD with the length and count rules, giving 409 on a folded-name duplicate and 422 `{field, msg}`.

  Test: accent-free match; no match inside "thiết kế"; switched-off topics are ignored; duplicate names are refused.
- [x] 1.3 `respond()`:
  - check the question before retrieval and the chosen answer before the suffixes;
  - on a hit: `FALLBACK`, no sources or images, `answered = False`, a handoff lead, no `_log_gap`, and `out["chu_de_cam"]`.

  Test, using the knowledge base: a question hit; a draft-only hit; a switched-off topic; no gap row; the lead exists.
- [x] 1.4 Storage and the API:
  - `/chat` stores the hit through `add_turn(..., chu_de_cam=)` and strips it from the public reply;
  - `_messages(staff=True)` returns it, and the visitor restore does not;
  - endpoints `GET/POST/PATCH /forbidden-topics`, `DELETE` (approvers only) and `POST /forbidden-topics/try`.

  Test: the roles (sales 403, anonymous 401, content delete 403); the public `/chat` response and `GET /chat/{id}` contain neither the topic name nor its keywords; the staff detail shows it.

## 2. Forbidden topics (frontend)

- [x] 2.1 `src/api.js` helpers. In `KnowledgeView.vue`, add a "Chủ đề cấm" tab with:
  - a list with an on/off switch;
  - a create/edit form with keywords one per line and errors at the field;
  - a "Thử câu" box;
  - delete for approvers only.
- [x] 2.2 `ConversationsView.vue`: show "Chặn: <ten> (câu hỏi|câu trả lời)" on the blocked reply, and hide "Soạn đáp án" for that question.
- [x] 2.3 Verify in the browser with a throw-away topic and conversation:
  - create "Đối thủ" with "công ty khác";
  - "Thử câu" shows the hit;
  - asking in the chat box gives the handoff message;
  - the staff detail shows the block;
  - the tab works by keyboard and has no sideways scroll at 360px;
  - clean up afterwards.

## 3. Sitemap and robots.txt

- [x] 3.1 `GET /sitemap.xml` in `api.py`:
  - public pages, project pages (folder `_` → `-`, only folders with a published photo) and published `/khong-gian/<id>`;
  - `lastmod` from the latest `review_log` entry, or else today (`space` has no timestamp);
  - the base address from `D3_FRONTEND_URL`, with a fallback;
  - escaped XML, `application/xml`, `max-age=300`.

  Test, on throw-away published spaces: draft and internal photos are absent; a take-down removes the photo and an emptied project; addresses are absolute; no private paths; the XML parses.
- [x] 3.2 `nginx.conf`: add `location = /prj1/sitemap.xml` (proxied to the backend) and `location = /robots.txt`. Add `public/robots.txt` with the Disallow lines, a `Sitemap:` line and a comment on changing the host when deploying. Rebuild the web image, then check that `curl :8080/prj1/sitemap.xml` and `curl :8080/robots.txt` both work.

## 4. Items linked to service packages

- [x] 4.1 Schema: `ALTER TABLE mon_do ADD COLUMN IF NOT EXISTS dich_vu_id int REFERENCES kb_chunk(id) ON DELETE SET NULL`. In `items.py`:
  - add `dich_vu_id` to the editable fields;
  - accept it only when it is a `kind = 'service'` chunk, else 422;
  - return `dich_vu` (the title) in `get` and `list_with_usage`.

  Add the endpoint `GET /items/services` (STAFF). Test: a faq id is refused; deleting the chunk clears the link and keeps the item.
- [x] 4.2 `with_services()`:
  - an item's service (in use, `kind = 'service'`) wins over the label mapping;
  - an item without one falls back to the label mapping;
  - a hand-placed point without one gets none;
  - one query, reusing the caller's connection.

  Test the three spec scenarios on `GET /spaces/{id}`, and check that the public response still has no supplier or note.
- [x] 4.3 `ItemsView.vue` and the item form in `HotspotEditor.vue`: a service `<select>` ("Không gắn dịch vụ" first, "(chưa dùng)" on entries not in use). The library list shows each item's service. Verify in the browser:
  - link a throw-away item to a service and place it on a throw-away published photo;
  - `GET /spaces/{id}` carries the service on that hotspot, and the visitor card still shows only the name;
  - there is no sideways scroll at 360px;
  - clean up afterwards.

## 5. Docs and checks

- [x] 5.1 Update `TONG-QUAN-DU-AN.md`:
  - UC09 and seq-3 step 15 are done;
  - seq-6 step 18 and roadmap 4.5 (sitemap and robots.txt) are done;
  - roadmap 1.9 (item services) is done;
  - the API table;
  - the deployment note on the robots.txt host.

  Run the full backend suite (no failures beyond the 8 known ones) and vitest.
