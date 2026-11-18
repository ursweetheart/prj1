# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Schema:** re-apply it with `docker compose exec -T db psql -U d3 -d d3 -q -v ON_ERROR_STOP=1 < backend/schema.sql`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.
- **Tests and the assistant model:** tests do not call the language model. They use questions the knowledge base answers, or monkeypatch `vertex.available` to `False`, so an unanswered question takes the fallback path.
- **Throw-away data:** test conversations and leads are created and removed by the tests. Test accounts use `@example.com`.
- **Tùng's styling stays untouched:** in `ChatWidget.vue`, only the script, the message list and new rules for the new button and notice change. Check with `git diff src/components/ChatWidget.vue` that the pill markup and its existing CSS rules are unchanged.

## 1. Backend

- [x] 1.1 Schema: add tables `hoi_thoai` and `tin_nhan` (with their indexes) and the column `lead.hoi_thoai_id`, as in the design.

  Verify that `schema.sql` applies twice without errors.
- [x] 1.2 Create `backend/pipeline/conversations.py` with `mask`, `merge`, `start_or_get`, `add_turn`, `link_lead`, `read`, `delete`, `purge`, `list_for_staff` and `detail_for_staff`.

  Verify with tests:
  - `mask` turns "0912 345 678", "0912.345.678", "+84 912 345 678" and "a.b@c.vn" into placeholders, and leaves "70m2", "2025" and "3 phòng ngủ" alone;
  - `merge` replaces only with non-null values;
  - `start_or_get` makes a new 32-hex id for a missing, unknown or malformed id, and links a session only when its `phien_truy_cap` row exists;
  - `add_turn` stores masked text and updates the counts and constraints;
  - `purge` deletes a conversation whose `cap_nhat` is 91 days old, with its messages, and keeps one 89 days old.
- [x] 1.3 Wire it into the chat:
  - `POST /chat` takes and returns `hoi_thoai_id`, reads the stored history and constraints, and stores the turn;
  - `respond()` merges the constraints, uses the merged `space_type` / `design_style` for example photos, and puts the merged constraints in the lead's request;
  - a created lead is linked, and a handoff sets `da_chuyen_nguoi_that`;
  - add `GET /chat/{hid}` and `DELETE /chat/{hid}`;
  - the daily purge goes in the maintenance loop.

  Verify with API tests:
  - two questions without `phien_id` give one conversation with 4 messages and no session;
  - with a consented session, it is linked;
  - "chung cư 70m2" then a price question with "wabi-sabi" gives a `price` lead whose request has `chung_cu`, 70 and Wabi-sabi, and the conversation shows that `lead_id`;
  - an unanswered question gives `chua_tra_loi = 1` and `da_chuyen_nguoi_that`;
  - the lead keeps the unmasked phone in `contact` while the stored message is masked;
  - `GET /chat/{hid}` returns the masked turns;
  - after `DELETE`, it gives 404;
  - a malformed id gives 404;
  - a client `history` is ignored once turns are stored.
- [x] 1.4 Staff endpoints: `GET /conversations?loc=&days=&offset=` and `GET /conversations/{hid}` for `content`, `sales`, `lead_architect` and `admin`.

  Verify with API tests:
  - visitor and architect get 403, and anonymous 401;
  - the filters `chua_tra_loi` and `lead` keep only matching conversations;
  - `days` other than 7, 30 or 90 gives 422;
  - the list holds no `phien_id` and no unmasked phone;
  - the detail has the sources and scores of each answer.

## 2. Frontend

- [x] 2.1 `src/api.js`: `sendChat` sends `hoi_thoai_id` and sends `phien_id` whenever the banner was accepted (`gui_ho_so` only when ticked). Add `getChat`, `deleteChat`, `listConversations` and `getConversation`.

  `ChatWidget.vue` (script and message list only):
  - stores the id under `d3_hoi_thoai`, in `localStorage` with consent and `sessionStorage` without;
  - restores the conversation on first open;
  - has a "Bắt đầu cuộc mới" button;
  - shows the 90-day notice line.

  Verify in the browser:
  - **without consent:** two questions survive a reload but not a new tab session;
  - **with consent:** they survive closing and reopening the browser context (same storage);
  - "Bắt đầu cuộc mới" empties the box, and the old id gives 404;
  - the button is reachable by Tab;
  - no sideways scroll at 360px with the chat open;
  - `git diff` shows the pill markup and existing CSS unchanged.
- [x] 2.2 Create `ConversationsView.vue` at `/quan-tri/hoi-thoai`:
  - filters and period;
  - expandable rows (keyboard);
  - the thread with sources, scores and the "Chưa trả lời được" mark;
  - the constraints;
  - "Đã chuyển người thật";
  - links to the lead and to "Soạn đáp án".

  Also: `KnowledgeView.vue` handles `#soan=`, and "Hội thoại" is added to `SiteNav.vue` role links.

  Verify in the browser, as a content editor, after asking the chatbot an answerable and an unanswerable question:
  - both conversations are listed;
  - "Chưa trả lời được" keeps only the second;
  - opening it shows the thread and the constraints;
  - "Soạn đáp án" opens `/quan-tri/tri-thuc` with the question prefilled, linked to its gap;
  - a sales user sees the page, a visitor is redirected;
  - 360px has no sideways scroll;
  - Enter and Space open and close a row.

  Remove the test conversations and leads afterwards.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - roadmap 2.8;
  - UC09 (chat) and known issue 8 ("Hội thoại chỉ lưu trong `lead.conversation`");
  - seq-3 step 18;
  - the API table;
  - the 90-day retention and masking note.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
