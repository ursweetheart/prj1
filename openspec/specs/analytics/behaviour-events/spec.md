# analytics/behaviour-events Specification

## Purpose

Records how visitors use the site beyond the photos they view and save (UC21; seq-4, act-7, dfd-2-5; class-4 SuKien): which pages they read and for how long, which calls to action and forms work, how much they chat, share and filter. It shows the results to the people who read the trend dashboard, under the same consent rule as every other behaviour signal.

## Requirements

### Requirement: Same consent rule for every event
Each new event SHALL be stored with its details and the visitor's session only when the visitor accepted data collection. Otherwise only that day's anonymous count for the event type SHALL increase. Events from signed-in staff accounts and from staff pages SHALL NOT be recorded.

#### Scenario: Visitor who declined
- **WHEN** a visitor who declined the banner reads `/uoc-tinh` and leaves
- **THEN** no event row is stored, and the day's `xem_trang` count increases by one

#### Scenario: Staff browsing
- **WHEN** a signed-in architect reads `/du-an/beaumont-lounge`
- **THEN** nothing is recorded

### Requirement: Page and project views with time and scroll
When a consenting visitor leaves a page, by navigating or by closing or hiding the tab, the system SHALL record a page view with:
- the page's route pattern;
- the time spent, in milliseconds, at most 24 hours;
- the deepest scroll reached, from 0 to 1.

A project page view SHALL be recorded as a project view naming the project's slug. A share code or any other secret in the path, the query string and the hash SHALL NOT be stored.

#### Scenario: Project page
- **WHEN** a consenting visitor spends 40 seconds on `/du-an/beaumont-lounge`, scrolls to the end and opens another page
- **THEN** a `xem_du_an` event is stored with the route `/du-an/:slug`, the object `beaumont-lounge`, about 40,000 ms and a scroll depth of 1

#### Scenario: Shared brief
- **WHEN** a consenting visitor reads `/bo-suu-tap/xem/ABC123`
- **THEN** the stored page is `/bo-suu-tap/xem/:ma` and `ABC123` appears nowhere in the event

### Requirement: Calls to action and forms
The system SHALL record a `bam_CTA` event when a link to the contact page, the cost estimate or the style quiz is clicked anywhere on the site, with the target and the page it was on. It SHALL record a `gui_form` event when the contact form, the brief or the emailed estimate is sent successfully, naming which.

#### Scenario: Home CTA
- **WHEN** a consenting visitor clicks the home page link to `/lien-he`
- **THEN** a `bam_CTA` event is stored with the target `/lien-he` and the page `/`

#### Scenario: Contact form sent
- **WHEN** a consenting visitor sends the contact form successfully
- **THEN** a `gui_form` event names `lien_he`, and contains none of the visitor's fields

### Requirement: Chat, share and filters
The system SHALL record a `nhan_chatbot` event when a chat message gets its answer, and a `chia_se` event when the brief's share link is copied. It SHALL record an `ap_dung_bo_loc` event when the space explorer's filters settle on a new non-empty choice, with the chosen values, once per distinct choice.

#### Scenario: Filters
- **WHEN** a consenting visitor ticks "Japandi" and then "Phòng khách" on `/khong-gian` and stops
- **THEN** one `ap_dung_bo_loc` event is stored with both values

### Requirement: No personal text in events
No event SHALL contain a name, phone number, email address, message text or chat text.

#### Scenario: Chat message
- **WHEN** a consenting visitor writes their phone number in the chat
- **THEN** the `nhan_chatbot` event holds no text from the message

### Requirement: Behaviour section on the trend dashboard
The trend dashboard SHALL show, for its selected period and to its viewers:
- the most viewed pages, with their views, average time and average scroll depth;
- the most viewed projects;
- CTA clicks by target and by page;
- forms sent by kind;
- the number of chat messages and shares;
- the most used filter values;
- searches by kind;
- similar suggestions shown and accepted, with the acceptance rate;
- for each type, the anonymous count beside the consented count.

It SHALL contain only counts and averages.

#### Scenario: Reading the section
- **WHEN** consenting visitors viewed `/uoc-tinh` 10 times in the period, for 30 seconds each on average
- **THEN** the section lists `/uoc-tinh` with 10 views and about 30 s average time

#### Scenario: Suggestion acceptance
- **WHEN** similar suggestions were shown 40 times in the period and 10 were opened
- **THEN** the section shows 40 shown, 10 accepted, 25%

#### Scenario: Visitor asks
- **WHEN** a visitor requests the behaviour figures
- **THEN** the server answers 403

### Requirement: Existing scores unaffected
The new events SHALL NOT change the interest score, the trends, the project results, the weekly report totals or a lead's behaviour profile.

#### Scenario: Lead profile
- **WHEN** a consenting visitor viewed 3 photos and 5 pages and then sends the contact form with their views
- **THEN** the lead's profile counts 3 views

### Requirement: Events are sent in batches
The browser SHALL buffer events and send them as one batch every 5 seconds while it has any, and at once when the page is hidden or left (seq-4 steps 2-3, act-3 "Gửi sự kiện lên máy chủ theo lô"). A batch SHALL hold at most 50 events. Each event SHALL carry how many milliseconds before sending it happened, up to 10 minutes. The server SHALL store each event at its real time.

The server SHALL validate every event of a batch and the batch's consent state (seq-4 step 4). It SHALL refuse a batch with any invalid event (422), and store nothing from it. A single event sent in the earlier one-event form SHALL still be accepted.

#### Scenario: Several events in a few seconds
- **WHEN** a consenting visitor saves 2 photos and applies a filter within 3 seconds
- **THEN** one request carries the 3 events, and each is stored at the moment it happened

#### Scenario: Closing the tab
- **WHEN** a consenting visitor closes the tab 2 seconds after a CTA click
- **THEN** the click and the page view are sent before the tab closes

#### Scenario: Invalid event in a batch
- **WHEN** a batch holds an event with an unknown type
- **THEN** the server answers 422 and none of the batch's events is stored

### Requirement: Session details
For a consented session the browser SHALL send:
- an anonymous device id, a random value kept in the browser only while analytics consent is given;
- the traffic source: `truc_tiep`, `tim_kiem`, `mang_xa_hoi`, `gioi_thieu`, or a short campaign name from `utm_source`;
- the device type: `di_dong`, `may_tinh_bang` or `may_tinh`.

The server SHALL store them with the session, set its start at its first event and move its end to its latest event. A declined session SHALL send none of them.

#### Scenario: Visitor from a search engine on a phone
- **WHEN** a consenting visitor arrives from google.com on a phone
- **THEN** their session is stored with source `tim_kiem`, device `di_dong`, and start and end times

### Requirement: Object type on every event
Each stored event SHALL record the kind of object it is about (class-4 `loai_doi_tuong`):
- `khong_gian` for photo events;
- `du_an` for project views;
- `trang` for page views;
- `lien_ket` for CTA clicks;
- `form` for forms;
- `tim_kiem` for searches.

#### Scenario: Project view
- **WHEN** a `xem_du_an` event is stored
- **THEN** its object type is `du_an` and its object is the project slug

### Requirement: Search and similar-space events
The system SHALL record (dfd-2-1 1.3, seq-2 steps 12 and 14):
- `tim_kiem` when a visitor searches by photo or by description, naming the kind (`anh` or `mo_ta`) and the number of results;
- `xem_goi_y_tuong_tu` when similar spaces are shown for a space;
- `chon_goi_y` when the visitor opens one of those similar spaces, naming the source space.

The search text and the uploaded photo SHALL NOT be stored in any event.

#### Scenario: Description search
- **WHEN** a consenting visitor searches "phòng khách gỗ ấm" and gets 12 results
- **THEN** a `tim_kiem` event with kind `mo_ta` and 12 results is stored, and the words are stored nowhere

#### Scenario: Suggestion accepted
- **WHEN** a consenting visitor on space 12 sees similar spaces and opens space 30 from them
- **THEN** `xem_goi_y_tuong_tu` for space 12 and `chon_goi_y` for space 30 with source 12 are stored
