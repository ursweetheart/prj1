# Proposal

## Why

The chatbot answers from `kb_chunk`. The only way to change what it says is to edit `backend/kb/*.json` and run `python -m pipeline.assistant <file>`. Content staff, who own the answers in the diagrams (UC16, usecase-3, seq-16), cannot do that. As a result:
- all 11 live entries are still sample text marked "[DỮ LIỆU MẪU]";
- the 8 AI-written project descriptions in `kb/generated.json` have never been reviewed or loaded;
- the 15 questions the chatbot could not answer (`khoang_trong_tri_thuc`) are seen by nobody.

Roadmap 1.6, replacing the samples with D3's real prices, process and FAQ, waits on this screen (roadmap 1.5).

seq-16 also sets one rule the CLI cannot enforce: **"Giá chỉ được nêu sau khi được duyệt"**. An entry with prices is used only after the lead architect approves it.

## What Changes

- **`/quan-tri/tri-thuc`** for content staff, the lead architect and admin:
  - a list of entries with kind, title, status and source, a search box and status filters;
  - an editor for title, kind, match phrases (what the question is matched against) and answer text.
- **A status for each entry**:
  - "Nháp" (draft);
  - "Chờ duyệt" (waiting for the lead architect);
  - "Đang dùng" (in use);
  - "Tắt" (off).

  **Only "Đang dùng" entries are used by the chatbot.**
- **Who may switch an entry on:**
  - An entry that needs price approval (kind `price`, or an answer that states an amount of money) can only be switched on by the lead architect or admin. Content staff send it for approval.
  - Content staff switch on general entries themselves.
  - When content staff change the answer of a live price entry, it goes back to "Chờ duyệt" and the chatbot stops using it until it is approved again.
- **Saving re-embeds** title and match phrases, so a change is used from the next question.
- **AI drafts:**
  - Loading a file whose entries carry "[AI SINH - CHƯA DUYỆT]" now stores them as "Chờ duyệt" instead of live.
  - The marker is removed when someone approves an entry.
  - The 8 drafts in `kb/generated.json` are loaded this way.
- **Sample entries** keep their "[DỮ LIỆU MẪU]" marker and show a "Dữ liệu mẫu" badge until the marker is removed from the text.
- **Unanswered questions:**
  - a tab lists them, grouped by the same question, most-asked first, with the words the taxonomy did not know;
  - "Soạn đáp án" opens a new entry pre-filled from the question;
  - when that entry is switched on, the questions it answers are closed;
  - "Bỏ qua" closes a question without an entry.
- **Delete** an entry (approvers only).
- **Service titles that hotspots link to** cannot be renamed or deleted (409 with an explanation).
- **The change log:** every change is logged.
- **A "Tri thức" link** in the staff menu.

## Capabilities

### New Capabilities
- `assistant-knowledge`: managing the chatbot's knowledge entries and their statuses, the price-approval rule, AI drafts, and turning unanswered questions into entries.

### Modified Capabilities
None. No main spec covers the chatbot's knowledge base yet: `minimal-cta-chat` covers the chat widget's look.

## Impact

- **Backend:**
  - `backend/schema.sql`:
    - `kb_chunk` adds `cum_tu_khop`, `trang_thai`, `nguon`, `updated_at` and `updated_by`;
    - `khoang_trong_tri_thuc` adds `trang_thai` and `kb_chunk_id`;
    - a new table `nhat_ky_tri_thuc`;
    - existing rows become "Đang dùng".
  - `backend/pipeline/assistant.py`:
    - `retrieve` reads only "Đang dùng";
    - `load_kb` stores AI drafts as "Chờ duyệt" and keeps the match phrases.
  - New `backend/pipeline/knowledge.py`.
  - `backend/api.py`: `/knowledge` endpoints.
  - New `backend/tests/test_knowledge.py`.
- **Frontend:**
  - `src/api.js`: the new calls;
  - new `src/views/KnowledgeView.vue`;
  - `src/router/index.js`;
  - `src/components/SiteNav.vue` (the "Tri thức" link).
- **Data:** `kb/generated.json` is loaded once as "Chờ duyệt" (8 entries). The live sample entries are unchanged.
- **Out of scope:**
  - writing D3's real content (roadmap 1.6, a content task);
  - photo descriptions used by the photo RAG (the photo transcripts);
  - version history or undo of entries;
  - answer quality evaluation (`eval_assistant.py` stays as it is).
