## Purpose

Keeps the assistant away from topics D3 Studio does not want it to discuss (seq-3 step 15). Staff keep a list of topics with keywords; a question or answer that touches a switched-on topic is handed to a person instead, without telling the visitor why, and staff can see which topic stopped it.

## ADDED Requirements

### Requirement: Who manages forbidden topics
Viewing and editing forbidden topics SHALL be limited to content staff, the lead architect and admin. Other signed-in users SHALL get 403, and anonymous requests 401. Deleting a topic SHALL be limited to the lead architect and admin; content staff SHALL instead switch a topic off.

#### Scenario: Sales opens the list
- **WHEN** a sales user requests the forbidden topics
- **THEN** the server answers 403

#### Scenario: Content deletes
- **WHEN** a content editor deletes a topic
- **THEN** the server answers 403 and the topic stays

### Requirement: A topic has a name, keywords and a switch
Each forbidden topic SHALL have:
- a name, 1 to 80 characters, unique regardless of case and accents;
- one to 30 keywords or phrases, each 2 to 60 characters;
- an optional staff note of at most 300 characters;
- an on/off switch, on by default.

Keywords SHALL match regardless of case and accents, and only as whole words or phrases. Switched-off topics SHALL NOT be checked.

#### Scenario: Accent-free match
- **WHEN** a topic "Đối thủ" has the keyword "công ty khác" and a visitor writes "cong ty khac lam re hon khong"
- **THEN** the question hits the topic

#### Scenario: No partial-word match
- **WHEN** a topic has the keyword "thuế" and the answer contains "thiết kế"
- **THEN** the answer does not hit the topic

#### Scenario: Duplicate name
- **WHEN** someone creates "doi thu" while "Đối thủ" exists
- **THEN** the server answers 409 naming the existing topic

### Requirement: The assistant checks question and answer
Before an answer is shown, the assistant SHALL check both the visitor's question and the draft answer against every switched-on topic. The check SHALL cover answers from the knowledge base and answers written from photos alike. The existing check for money amounts and promises SHALL stay in place besides the list.

#### Scenario: Forbidden question
- **WHEN** a visitor asks about a switched-on topic
- **THEN** no knowledge or photo answer is shown

#### Scenario: Forbidden word only in the draft
- **WHEN** the question is harmless but the draft answer from the knowledge base contains a switched-on keyword
- **THEN** the draft is not shown

#### Scenario: Switched-off topic
- **WHEN** the only matching topic is switched off
- **THEN** the answer is shown as usual

### Requirement: A hit hands the visitor to a person
On a hit, the visitor SHALL see the same handoff message an unanswered question gets, with no sources and no photos. The message SHALL NOT name the topic or its keywords. A handoff lead SHALL be created as for an unanswered question. A hit SHALL NOT be logged as a knowledge gap.

#### Scenario: Hit
- **WHEN** a visitor's question hits the topic "Đối thủ"
- **THEN** the reply is the handoff message, the reply has no sources and no images, a handoff lead exists, and no new knowledge-gap row exists

#### Scenario: Topic not revealed
- **WHEN** a question hits a topic
- **THEN** the public response contains neither the topic's name nor its keywords

### Requirement: Staff see which topic was hit
The stored conversation SHALL record which topic was hit on the assistant's message, and whether the question or the answer hit it. The staff conversation detail SHALL show "Chặn: <topic name>" on that message. The conversation list filter "Chưa trả lời được" SHALL include conversations with a hit. Visitors restoring their own conversation SHALL NOT receive the topic.

#### Scenario: Staff opens a blocked conversation
- **WHEN** a content editor opens a conversation whose second question hit "Đối thủ"
- **THEN** the second reply shows "Chặn: Đối thủ (câu hỏi)"

#### Scenario: Visitor restores
- **WHEN** the visitor reloads the page and the chat box restores that conversation
- **THEN** the restored data has no topic name

### Requirement: Manage topics on the knowledge screen
`/quan-tri/tri-thuc` SHALL have a "Chủ đề cấm" tab. On it, staff can:
- list topics with their keywords and switch, and switch a topic on or off;
- create and edit topics;
- try a sample sentence against the list, without asking the assistant.

The tab SHALL be usable by keyboard, with errors shown at their field, and SHALL have no sideways scroll at 360px.

#### Scenario: Try a sentence
- **WHEN** a content editor types "bên công ty khác báo rẻ hơn" in "Thử câu"
- **THEN** the tab shows that "Đối thủ" is hit, through "công ty khác"

#### Scenario: Empty keyword list
- **WHEN** an editor saves a topic with no keyword
- **THEN** the save is refused with the error shown at the keyword field and focus moved there
