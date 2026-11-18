# Proposal

## Why

The assistant forgets everything:
- The chat box keeps the conversation only in the page's memory, so a reload or a later visit starts over.
- The server keeps a conversation only when it turns into a lead.
- Each question is read on its own. If a visitor says "chung cư 70m2" and then asks "phong cách wabi-sabi thì sao?", the second question has lost the project type and the area.

The design asks for more:
- **Seq-3 step 18:** "Lưu hội thoại và các thuộc tính được đề cập".
- **Class-4:** `HoiThoai` (collected constraints, handed to a person, start) and `TinNhan` (role, text, sources, best similarity, time).
- **Roadmap 2.8:** "lọc theo metadata (diện tích, loại công trình khách nói), lưu lịch sử hội thoại".

Staff also cannot see how the assistant actually answers. They see unanswered questions one by one, never the conversation around them.

## What Changes

- **Conversations are stored on the server**, with each message: role, text, the sources used and the best similarity score.
  - Every conversation is kept **anonymously**. It is linked to the visitor's session only when the visitor accepted the tracking banner.
  - **Phone numbers and email addresses typed in the chat are masked** in the stored text. A lead keeps its own contact as today.
  - Conversations untouched for **90 days are deleted** automatically.
- **Constraints carry over within a conversation.** Project type, space type, area and style are collected across the visitor's messages and kept with the conversation.
  - A later question uses what was said earlier: for the example photos it shows, and for the request saved with a lead.
  - A newer value replaces an older one ("à không, nhà phố").
- **The chat box remembers:**
  - **Without consent:** the conversation lasts as long as the browser tab, and survives a reload.
  - **With consent:** it is restored on a later visit from the same browser.
  - "Bắt đầu cuộc mới" starts a fresh conversation and deletes the old one from the server.
  - Only the chat box's script changes. Tùng's "Hỏi trợ lý" pill and its styles stay as they are.
- **Staff view `/quan-tri/hoi-thoai`** (content, sales, lead architect, admin):
  - conversations newest first, filtered by "Chưa trả lời được" / "Thành khách tiềm năng" / all, and by period;
  - each conversation shows its messages, the collected constraints, the sources and scores of each answer, and a link to its lead;
  - each unanswered question links to "Soạn đáp án" in `/quan-tri/tri-thuc`;
  - no visitor contact is shown beyond the masked text; the lead page stays the place for contacts.
- **A lead created from a chat is linked to its conversation,** and a handoff marks the conversation "đã chuyển người thật".

**Decisions taken with the user:**
- Keep all conversations anonymously for 90 days, rather than only consented ones.
- Edit only the script of `ChatWidget.vue`.

## Capabilities

### New Capabilities
- `assistant-conversations`: storing chat conversations and messages, masking contacts, retention, carrying constraints across a conversation, restoring a conversation in the chat box, and the staff conversation view.

### Modified Capabilities
None. `leads/lead-intake` keeps its rule that a chat lead stores its conversation; the lead now also points to the stored conversation, which adds to it without changing it. `assistant-knowledge` keeps the unanswered-question list as is.

## Impact

- **Backend:**
  - **New `backend/pipeline/conversations.py`:** start or continue a conversation, add messages, merge constraints, mask contacts, list and read for staff, delete, purge old ones.
  - **`backend/pipeline/assistant.py`:** `respond()` takes the conversation's history and constraints from the database.
  - **`backend/api.py`:**
    - `POST /chat` takes and returns `hoi_thoai_id`;
    - `GET /chat/{id}` and `DELETE /chat/{id}` (whoever holds the id);
    - `GET /conversations`, `GET /conversations/{id}` (staff);
    - the daily purge in the existing scheduler loop.
  - **New `backend/tests/test_conversations.py`.**
- **Schema:**
  - tables `hoi_thoai` and `tin_nhan`;
  - column `lead.hoi_thoai_id`.
- **Frontend:**
  - `src/api.js`;
  - `src/components/ChatWidget.vue` (script and message list only);
  - new `src/views/ConversationsView.vue`;
  - the route;
  - "Hội thoại" in the staff menu (`SiteNav.vue` role links, as earlier admin pages did).
- **Out of scope:**
  - conversations across devices for signed-in visitors;
  - full-text search over conversations;
  - exporting;
  - a staff reply inside the chat (handoff stays a lead, handled outside the system);
  - the forbidden-topics check (seq-3 step 15).
