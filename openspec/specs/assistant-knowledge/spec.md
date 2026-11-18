# assistant-knowledge Specification

## Purpose
Lets content staff and the lead architect manage what the chatbot answers from (UC16, seq-16): knowledge entries with a status, prices approved before they are said, AI drafts reviewed before use, and questions the chatbot could not answer turned into new entries.

## Requirements

### Requirement: Who manages knowledge
Viewing and editing knowledge entries and unanswered questions SHALL be limited to content staff, the lead architect and admin. Other signed-in users SHALL get 403 and anonymous requests 401. Deleting an entry SHALL be limited to the lead architect and admin.

#### Scenario: Sales opens the list
- **WHEN** a sales user requests the knowledge entries
- **THEN** the server answers 403

#### Scenario: Content deletes
- **WHEN** a content editor deletes an entry
- **THEN** the server answers 403 and the entry stays

### Requirement: Entry status decides what the chatbot uses
Each entry SHALL have one status: "Nháp", "Chờ duyệt", "Đang dùng" or "Tắt". The chatbot SHALL answer only from entries that are "Đang dùng". A change to a live entry's title or match phrases SHALL be used from the next question.

#### Scenario: Switched off
- **WHEN** the entry "Chính sách bảo hành" is set to "Tắt"
- **THEN** asking the chatbot "bảo hành bao lâu" no longer returns that entry's answer

#### Scenario: New wording is matched at once
- **WHEN** a content editor adds "đổi trả hàng" to the match phrases of a live entry and saves
- **THEN** that entry's embedding is rebuilt from the new title and match phrases before the save returns, so the next knowledge search for "đổi trả hàng" ranks it first

### Requirement: No prices are said
The site shows no prices (the owner's decision, 2026-11-18). The chatbot SHALL NOT use an entry of kind `price` or an entry whose answer states an amount of money, even when it is in use, and SHALL drop any sentence of a drafted answer that states an amount. A price question SHALL still offer to have an architect call back and SHALL still create a lead. The approval rule below keeps applying to such entries, which stay internal.

#### Scenario: Live price entry
- **WHEN** an approved price entry is in use and a visitor asks how much a villa interior costs
- **THEN** the answer names no amount and does not cite that entry, and the visitor is asked to leave a phone number or email

#### Scenario: Amount slipped into an answer
- **WHEN** a drafted answer says "Phòng khách 70m2 dùng gỗ sồi. Chi phí khoảng 500 triệu."
- **THEN** the visitor sees "Phòng khách 70m2 dùng gỗ sồi."

### Requirement: Prices are said only after approval
An entry SHALL need price approval when its kind is `price` or its answer states an amount of money (a number followed by a money unit such as "triệu", "tỷ", "nghìn", "đ", "VND" or "/m²"). Only the lead architect or admin SHALL switch such an entry on. Content staff SHALL send it to "Chờ duyệt" instead. When content staff change the answer of a live entry that needs price approval, it SHALL go back to "Chờ duyệt" and stop being used until approved.

#### Scenario: Content writes a price
- **WHEN** a content editor saves "Phí thiết kế từ 250.000 đ/m²" and presses "Bật sử dụng"
- **THEN** the server answers 403 for switching it on, the entry is "Chờ duyệt", and the lead architect sees it waiting

#### Scenario: Lead architect approves
- **WHEN** the lead architect switches that entry on
- **THEN** it is "Đang dùng" and the chatbot can quote it

#### Scenario: General entry
- **WHEN** a content editor writes "Quy trình 5 bước…" without amounts and switches it on
- **THEN** it is "Đang dùng" without approval

#### Scenario: Edited price goes back for approval
- **WHEN** a content editor changes the amount in a live price entry
- **THEN** it becomes "Chờ duyệt" and the chatbot stops using it

### Requirement: AI drafts are reviewed before use
Entries loaded from a file whose answer starts with "[AI SINH - CHƯA DUYỆT]" SHALL be stored as "Chờ duyệt", not used. Switching such an entry on SHALL remove that marker from its answer. Entries marked "[DỮ LIỆU MẪU]" SHALL show a "Dữ liệu mẫu" badge while the marker is in the text.

#### Scenario: Load the generated drafts
- **WHEN** `kb/generated.json` is loaded
- **THEN** its 8 entries are "Chờ duyệt" and the chatbot does not answer from them

#### Scenario: Approve a draft
- **WHEN** the lead architect switches one of them on
- **THEN** its answer no longer starts with the marker and the chatbot can use it

### Requirement: Edit and create entries
A permitted user SHALL be able to create an entry and edit its title, kind (price, faq, service, project), match phrases and answer. Titles SHALL be unique. A service title that hotspots link to SHALL NOT be renamed or deleted, and the screen SHALL say why. Every create, edit, status change and delete SHALL be logged with who, when, and what changed.

#### Scenario: Duplicate title
- **WHEN** a content editor creates an entry titled "Chính sách bảo hành", which already exists
- **THEN** the server answers 409 and the form says the title is taken

#### Scenario: Linked service
- **WHEN** someone renames "Dịch vụ thiết kế phòng khách"
- **THEN** the server answers 409, because sofa and TV hotspots link to that title

### Requirement: Unanswered questions
The screen SHALL list the questions the chatbot could not answer that are still open, grouped by the same question regardless of case and accents, with how many times it was asked, when last, and the words the taxonomy did not know, most asked first. "Soạn đáp án" SHALL open a new entry with the question as its match phrases. When that entry is switched on, the questions in its group SHALL be closed and linked to it. "Bỏ qua" SHALL close a group without an entry.

#### Scenario: Turn a question into an entry
- **WHEN** "có làm nội thất văn phòng không" was asked 3 times and a content editor writes an answer from it and switches it on
- **THEN** the 3 questions are closed and linked to the new entry, and the group leaves the open list

#### Scenario: Dismiss
- **WHEN** a content editor presses "Bỏ qua" on an off-topic question
- **THEN** it leaves the open list and no entry is made

### Requirement: Usable on a phone and by keyboard
The knowledge screen SHALL be usable at 360px without sideways page scroll, and every action SHALL be reachable by keyboard, with form errors shown next to their field.

#### Scenario: Phone
- **WHEN** a content editor opens `/quan-tri/tri-thuc` on a 360px screen
- **THEN** the list and editor are readable and the page does not scroll sideways
