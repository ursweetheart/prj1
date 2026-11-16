# Design

## Context

- **`POST /chat`** (public, rate-limited 20/min) takes `{message, history[≤40], contact?, phien_id?, gui_ho_so}`. The history is held by the client.
- **`assistant.respond()`:**
  - parses the current message only (`parse_request` → `project_type`, `space_type`, `area_m2`, `design_style`, `price_intent`, `appointment_intent`);
  - retrieves from the knowledge base, falling back to photo RAG (Gemini) with the last 4 turns;
  - logs a knowledge gap when nothing answers;
  - creates a `chat` lead (`handoff` / `price` / `appointment`) holding the whole conversation and `contact`.
- **`ChatWidget.vue`** keeps `turns` in memory only. It sends `phien_id` only when the visitor accepted the banner *and* ticked "send what I viewed" (`viewsConsent`).
  - Tùng changed only the "Hỏi trợ lý" pill markup and CSS, in commit `f37d03a`; the script and message list are ours.
- **Sessions.** `phien_truy_cap` rows exist only for consented sessions; the token lives in `sessionStorage` (`visitId()`). `leads.create_lead` attaches a session and a profile only with `gui_ho_so` and an existing session row.
- **Class-4:**
  - `HoiThoai(ma uuid, rang_buoc_da_thu_thap json, da_chuyen_nguoi_that bool, bat_dau)`, which belongs to a `PhienTruyCap` (0..1) and becomes a `KhachTiemNang` (0..1);
  - `TinNhan(ma, vai_tro, noi_dung, nguon_tham_chieu json, diem_tuong_dong_cao_nhat, thoi_diem)`.
- **The scheduler loop** in `api.py` (weekly report) already runs every 10 minutes.

## Goals / Non-Goals

**Goals:**
- Conversations and messages stored as the class diagram describes.
- No stored contact details, and no visitor link without consent.
- Constraints remembered across messages.
- The chat box restores itself.
- Staff can read conversations.

**Non-Goals:**
- Accounts across devices.
- Staff replying in the chat.
- Search and export.
- The forbidden-topics filter.
- Changing how the knowledge base or photo RAG pick answers.

## Decisions

### 1. Schema
```sql
CREATE TABLE IF NOT EXISTS hoi_thoai (
  id text PRIMARY KEY,                -- 32 hex chars, random (uuid4().hex): possession = access for the visitor
  phien_id text REFERENCES phien_truy_cap(id) ON DELETE SET NULL,  -- only for a consented, existing session
  rang_buoc jsonb NOT NULL DEFAULT '{}',   -- project_type, space_type, area_m2, design_style collected so far
  da_chuyen_nguoi_that boolean NOT NULL DEFAULT false,
  bat_dau timestamptz NOT NULL DEFAULT now(),
  cap_nhat timestamptz NOT NULL DEFAULT now(),
  so_tin_nhan int NOT NULL DEFAULT 0,
  chua_tra_loi int NOT NULL DEFAULT 0      -- unanswered assistant messages, for the staff filter
);
CREATE TABLE IF NOT EXISTS tin_nhan (
  id serial PRIMARY KEY,
  hoi_thoai_id text NOT NULL REFERENCES hoi_thoai(id) ON DELETE CASCADE,
  vai_tro text NOT NULL CHECK (vai_tro IN ('khach', 'tro_ly')),
  noi_dung text NOT NULL,                  -- masked
  nguon jsonb,                             -- [{id, kind, title, score}] of an assistant message
  diem_cao_nhat real,
  tra_loi_duoc boolean,                    -- assistant messages only
  thoi_diem timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE lead ADD COLUMN IF NOT EXISTS hoi_thoai_id text REFERENCES hoi_thoai(id) ON DELETE SET NULL;
```
- **Indexes:** `tin_nhan (hoi_thoai_id, id)` and `hoi_thoai (cap_nhat DESC)`.
- **Assistant images** are not stored. A restored answer shows its text and sources, but not the example photos. This keeps the rows small and avoids showing photos that may have been unpublished since.

### 2. `pipeline/conversations.py`
- **`mask(text)`:**
  - Vietnamese phone numbers become `[số điện thoại]`. The pattern is `(\+84|0)` followed by 9 digits, with spaces, dots or dashes allowed between digits. This is the same rule as `LeadIn._phone`, applied inside free text.
  - Email addresses become `[email]`.
- **`merge(old, new)`:** a new non-null value of `project_type`, `space_type`, `area_m2` or `design_style` replaces the old one, and nothing is ever cleared. Intents are per message and are not stored.
- **`start_or_get(conn, hid, phien_id)`:**
  - with an unknown, missing or malformed id, it creates a new id;
  - `phien_id` is linked when sent. The client sends it only after consent, so the session row is created then (`ON CONFLICT DO NOTHING`), the same trust `/events` already uses. A visitor may chat before any tracked view created the row;
  - it returns `(id, rang_buoc, last messages)`.
- **`add_turn(conn, hid, user_text, answer, sources, best, answered, rang_buoc)`:**
  - inserts both messages, the visitor's masked;
  - updates `cap_nhat`, `so_tin_nhan`, `chua_tra_loi` and `rang_buoc`.
- **Other functions:**
  - `link_lead(conn, hid, lead_id, handoff)`;
  - `read(conn, hid)` for the visitor;
  - `delete(conn, hid)`;
  - `purge(conn, days=90)`;
  - `list_for_staff(conn, filter, days, limit, offset)`;
  - `detail_for_staff(conn, hid)`.

### 3. `respond()` with a conversation
- `POST /chat` gets `hoi_thoai_id?`.
- **The handler:**
  1. calls `start_or_get`;
  2. calls `respond(message, history=<stored turns, unmasked text is not available>, …, rang_buoc=<stored>)`;
  3. calls `add_turn`;
  4. if a lead was created, calls `link_lead`;
  5. returns `hoi_thoai_id` with the answer.
- **History source:** the server's own stored turns, last 4, as photo RAG uses. The client's `history` field stays accepted for older clients, but is ignored when the conversation has stored turns.
  - Stored visitor text is masked, which only removes phone numbers and emails from what the model sees. That is harmless.
- **Inside `respond`:**
  - `req = parse_request(message)` for the intents;
  - `merged = merge(rang_buoc, req)`;
  - example photos use `merged["space_type"]` and `merged["design_style"]`;
  - the lead's `request` is `{**merged, intents of this message}`;
  - the response returns `rang_buoc: merged` so the handler can store it.
- **The lead's `conversation`** stays the unmasked list, built from the client-visible turns as today. Consultants need what the visitor wrote, and leads are already personal data handled by sales. `contact` behaves as before.
- **The session id:** the chat box now sends `phien_id` whenever the banner was accepted, as `/events` does, and `gui_ho_so` only when ticked. `create_lead` already drops the session link unless `gui_ho_so`, so leads keep today's rule. The conversation is linked whenever the session row exists.

### 4. Visitor endpoints
- `GET /chat/{hid}` returns `{hoi_thoai_id, tin_nhan: [{vai_tro, noi_dung, nguon, thoi_diem}]}`, or 404.
- `DELETE /chat/{hid}` returns 204 (also when it was already gone).
- `hid` must match `^[0-9a-f]{32}$`; anything else is a 404 without a lookup.
- Both endpoints share the chat rate limit bucket.

### 5. Chat box (`ChatWidget.vue`, script and message list only)
- **Storage key `d3_hoi_thoai`:** `localStorage` when `consent.get() === 'yes'`, otherwise `sessionStorage`.
- **On first open:** if an id is stored, `GET /chat/{id}` fills `turns` (a 404 clears the id).
- **After each answer:** the returned `hoi_thoai_id` is stored.
- **"Bắt đầu cuộc mới":** a text button above the input, shown when there are turns. It calls `DELETE`, clears the id and `turns`, and moves focus to the input.
- **The pill markup and every existing style rule are left unchanged.** New rules are added only for the new button.

### 6. Staff
- `GET /conversations?loc=chua_tra_loi|lead|tat_ca&days=7|30|90&offset=` (`content` and `SALES`), 50 per page. Each row gives `{id, bat_dau, cap_nhat, so_tin_nhan, chua_tra_loi, da_chuyen_nguoi_that, lead_id, rang_buoc, cau_dau}`, where `cau_dau` is the first visitor message, masked.
- `GET /conversations/{hid}`: the messages, sources, scores, constraints and `lead_id`.
- `ConversationsView.vue` at `/quan-tri/hoi-thoai` (`page-top`):
  - filter chips and a period switch;
  - rows that expand, using a button with `aria-expanded`, into the message thread;
  - unanswered assistant messages marked "Chưa trả lời được", with "Soạn đáp án" → `/quan-tri/tri-thuc#soan=<encoded question>`;
  - a link to `/khach-hang` when a lead exists.
- **"Soạn đáp án" from a conversation:** `KnowledgeView.vue` (ours) reads `#soan=<question>` after loading the open gaps.
  - **When the question matches an open gap group** (same folded text, as the groups are formed), it calls the existing `answerGap(group)`, so those gaps close when the entry goes live.
  - **Otherwise** it opens `startNew` with the question as title and match phrase.
- **Nav:** "Hội thoại" in `SiteNav.vue` role links for `content` and `SALES`, the same one-line pattern as earlier admin pages.

### 7. Retention
`_weekly_once` in `api.py` becomes `_maintenance_once`. It also calls `conversations.purge(conn, 90)` once a day: the last purge time is kept in memory, and a restart just purges again, which is harmless.

## Risks / Trade-offs

- **[Visitors type other personal data, such as names or addresses]** → Only phones and emails can be masked reliably. The 90-day limit and staff-only access bound the rest. The chat box adds one line under the input, in the message area (not the pill): "Hội thoại được lưu ẩn danh 90 ngày để cải thiện trợ lý. Đừng gửi thông tin nhạy cảm."
- **[An id in `localStorage` is a bearer token]** → It only opens the conversation it names, which is masked text. Deleting it is the visitor's choice.
- **[Masked history reaches the model]** → Only phones and emails are removed, which the model does not need.
- **[Old leads have no conversation link]** → `hoi_thoai_id` stays null; the lead still has its own `conversation`.

## Migration Plan

- Apply `schema.sql` (it can be re-run) and rebuild the backend and web.
- Existing conversations are not backfilled.
- **Rollback:** the chat box ignores `hoi_thoai_id` if the API does not send it; the tables can stay.
