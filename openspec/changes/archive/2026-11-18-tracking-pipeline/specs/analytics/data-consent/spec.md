## ADDED Requirements

### Requirement: Three choices on first visit
On a visitor's first visit the site SHALL show a notice with three choices: "Đồng ý", "Từ chối" and "Tùy chỉnh" (act-7):
- **Đồng ý** turns on behaviour collection for analytics and for personalisation.
- **Từ chối** turns both off, so only anonymous daily counts are kept.
- **Tùy chỉnh** opens two switches, "Phân tích" and "Cá nhân hóa", and a "Lưu lựa chọn" button.

Personalisation SHALL require analytics, so turning analytics off turns personalisation off too. The notice SHALL be usable by keyboard, with its switches labelled for screen readers.

#### Scenario: Accept
- **WHEN** a visitor clicks "Đồng ý"
- **THEN** the notice closes, events are stored for their session, and the homepage suggestions may use their viewing

#### Scenario: Customise, analytics only
- **WHEN** a visitor opens "Tùy chỉnh", leaves "Phân tích" on, turns "Cá nhân hóa" off and saves
- **THEN** events are stored for their session, and the homepage suggestions do not use their viewing

#### Scenario: Personalisation depends on analytics
- **WHEN** a visitor turns "Phân tích" off in "Tùy chỉnh"
- **THEN** "Cá nhân hóa" turns off and cannot be turned on

### Requirement: The choice is kept and can be changed from the footer
The choice SHALL be remembered in the visitor's browser, and the notice SHALL NOT show again once answered. Every public page's footer SHALL offer "Cài đặt dữ liệu", which reopens the choices with the current answer selected. A new choice SHALL apply to the next event sent.

#### Scenario: Withdraw from the footer
- **WHEN** a visitor who accepted opens "Cài đặt dữ liệu" and chooses "Từ chối"
- **THEN** their next page view adds only to the anonymous daily count

### Requirement: Delete my data
The data settings SHALL offer "Xóa dữ liệu của tôi". After confirmation, the system SHALL delete every stored session of this browser (its current session and every session sharing its anonymous device id) with their events. It SHALL detach those sessions from conversations and leads without deleting the conversation or lead. It SHALL answer with how many sessions and events were deleted.

The request SHALL be logged with those counts and the time only, with no identifier. Figures already aggregated into the analytics store SHALL stay, because they hold no session data. Afterwards the browser SHALL start a new session and device id.

#### Scenario: Delete after browsing
- **WHEN** a consenting visitor who had 2 sessions with 30 events in this browser confirms "Xóa dữ liệu của tôi"
- **THEN** both sessions and their 30 events are gone, the visitor sees "Đã xóa 2 phiên, 30 sự kiện", and the deletion log has one row with those counts

#### Scenario: Only what the browser holds
- **WHEN** a delete request carries a session id and a device id
- **THEN** only the session with that id and the sessions carrying that device id are deleted; both ids are random values only that browser knows, an unknown id deletes nothing, and the endpoint is rate-limited

#### Scenario: Nothing stored
- **WHEN** a visitor who always declined asks to delete
- **THEN** the answer is "Không có dữ liệu nào được lưu" and nothing changes
