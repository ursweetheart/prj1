## Purpose

Keeps the assistant's conversations (seq-3 step 18; class-4 HoiThoai / TinNhan), so a visitor's conversation survives a reload, later questions use what the visitor already said, and staff can see how the assistant answers. It does this without keeping visitors' contact details or tying a conversation to a visitor who did not consent.

## ADDED Requirements

### Requirement: Conversations and messages are stored
Every chat conversation SHALL be stored with its messages in order, each with its role (visitor or assistant), text and time. An assistant message SHALL also record the sources it used, the best similarity score and whether it answered.

#### Scenario: Two questions
- **WHEN** a visitor asks two questions
- **THEN** one conversation with four messages is stored, the assistant's with their sources and scores

### Requirement: Visitor link only with consent
A conversation SHALL be linked to the visitor's session only when the visitor accepted data collection, and SHALL otherwise carry no visitor identifier. The chat box SHALL tell visitors that conversations are kept anonymously for 90 days.

#### Scenario: Visitor who declined collection
- **WHEN** a visitor who declined the banner asks two questions
- **THEN** one conversation with four messages is stored, with no session linked

#### Scenario: Visitor who accepted collection
- **WHEN** a visitor who accepted the banner asks a question
- **THEN** the stored conversation is linked to their session

### Requirement: Contact details are masked, old conversations removed
Phone numbers and email addresses in a visitor's message SHALL be replaced by a placeholder before the text is stored in the conversation. A lead created from the chat SHALL still receive the contact the visitor gave, as today. Conversations with no new message for 90 days SHALL be deleted automatically.

#### Scenario: Phone in a message
- **WHEN** a visitor writes "gọi em số 0912 345 678 nhé"
- **THEN** the stored message reads "gọi em số [số điện thoại] nhé"

#### Scenario: Old conversation
- **WHEN** a conversation's last message is 91 days old
- **THEN** it and its messages are deleted at the next daily clean-up

### Requirement: Constraints carry across the conversation
The project type, space type, area and style a visitor mentions SHALL be collected across the conversation. A newer value SHALL replace an older one. Each answer SHALL use the collected constraints, not only those in the current message, when choosing example photos. A lead created from the chat SHALL store the collected constraints as its request.

#### Scenario: Area said earlier
- **WHEN** a visitor first writes "chung cư 70m2" and later "phong cách wabi-sabi giá bao nhiêu"
- **THEN** the price lead stores project type chung cư, area 70 m² and style Wabi-sabi

#### Scenario: Visitor changes their mind
- **WHEN** a visitor said "chung cư" and later says "à không, nhà phố"
- **THEN** the collected project type is nhà phố

### Requirement: The chat box restores and can start over
Reloading the page SHALL restore the visitor's current conversation. For a visitor who accepted data collection, the conversation SHALL also be restored on a later visit from the same browser. For one who did not, it SHALL last only as long as the browser tab. "Bắt đầu cuộc mới" SHALL start an empty conversation and delete the previous one from the server. A conversation SHALL be readable and deletable only with its own unguessable id.

#### Scenario: Reload
- **WHEN** a visitor reloads the page after two questions
- **THEN** the chat box shows both questions and answers

#### Scenario: Start over
- **WHEN** the visitor presses "Bắt đầu cuộc mới"
- **THEN** the chat box is empty, and the old conversation can no longer be read from the server

### Requirement: Staff conversation view
Content editors, sales, the lead architect and admin SHALL see the conversations, newest first, filterable by "Chưa trả lời được", "Thành khách tiềm năng" or all, and by the last 7, 30 or 90 days. Visitors and architects SHALL get 403, and anonymous requests 401.

#### Scenario: Unanswered conversations
- **WHEN** a content editor filters by "Chưa trả lời được"
- **THEN** only conversations with at least one unanswered question are listed, and each such question links to "Soạn đáp án"

#### Scenario: Visitor
- **WHEN** a visitor requests the conversation list
- **THEN** the server answers 403

### Requirement: Conversation detail for staff
Opening a conversation SHALL show:
- its messages, with the sources and score of each answer;
- the collected constraints;
- whether it was handed to a person;
- a link to its lead;
- for each unanswered question, a link to write an answer in the knowledge screen.

#### Scenario: Open a conversation
- **WHEN** a content editor opens a conversation that ended in a price lead
- **THEN** they see each answer's sources and scores, the collected area and style, and a link to the lead

### Requirement: Lead and conversation are linked
A lead created from the chat SHALL point to its conversation. A handoff SHALL mark the conversation as handed to a person.

#### Scenario: Handoff
- **WHEN** the assistant cannot answer and creates a handoff lead
- **THEN** the conversation shows "Đã chuyển người thật" and links to that lead

### Requirement: Usable on a phone and by keyboard
The staff view SHALL have no sideways scroll at 360px. Every conversation SHALL open and close by keyboard. The chat box's new control SHALL be a keyboard-reachable button.

#### Scenario: Phone
- **WHEN** a content editor opens `/quan-tri/hoi-thoai` on a 360px screen
- **THEN** the list and an opened conversation are readable without scrolling sideways
