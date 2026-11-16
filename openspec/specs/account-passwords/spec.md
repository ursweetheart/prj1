# account-passwords Specification

## Purpose

Lets a person set a password from a link sent to their email, either to activate an account an admin created for them (seq-19 steps 7–11) or to recover a forgotten password (UC24). The links are short-lived and single-use, and nothing on these pages reveals which emails have accounts.

## Requirements

### Requirement: Password links
An invitation link SHALL be valid for 72 hours and a reset link for 1 hour. Each link SHALL work once. Issuing a new link of either kind for an account SHALL make that account's earlier unused links stop working. The system SHALL store only a one-way hash of each link's code. The code SHALL be carried after `#` in the URL, so it is not sent to the server when the page is opened.

#### Scenario: Used twice
- **WHEN** a person sets a password with a link and then opens the same link again
- **THEN** the page says the link has already been used and offers to send a new one

#### Scenario: Expired
- **WHEN** a reset link is used 61 minutes after it was sent
- **THEN** the password is not changed and the page says the link has expired

#### Scenario: Replaced
- **WHEN** a person asks for a reset twice and uses the first link
- **THEN** it is refused, and the second link works

### Requirement: Forgot password reveals nothing
"Quên mật khẩu" SHALL accept an email and always give the same answer, whether or not an account exists. A reset link SHALL be emailed only to an existing account that is not locked and whose address can receive mail. Requests SHALL be limited to 5 per 10 minutes per client.

#### Scenario: Unknown email
- **WHEN** someone asks for a reset for an email with no account
- **THEN** the answer is the same as for a real account, and nothing is sent

#### Scenario: Locked account
- **WHEN** someone asks for a reset for a locked account
- **THEN** the same answer is given, and no link is sent

### Requirement: Setting the password
The set-password page SHALL show whether the link is an invitation or a reset, and the account's email partly hidden. It SHALL accept a new password of 8 to 128 characters, entered twice. On success it SHALL set the password, use the link and sign the person in. A link for a locked account SHALL be refused.

#### Scenario: Invitation accepted
- **WHEN** an invited architect opens their link, sets a password and submits
- **THEN** they are signed in as an architect, and the account is no longer "Chưa kích hoạt"

#### Scenario: Passwords differ
- **WHEN** the two password fields differ
- **THEN** the page says so next to the field and nothing is sent

### Requirement: A reset ends other sessions
Setting a password through a reset link SHALL end every session of that account that was open before, as locking does.

#### Scenario: Signed in on another device
- **WHEN** a person is signed in on a laptop and resets their password from their phone
- **THEN** the laptop's next request is refused and asks them to sign in again

### Requirement: Without email
When outgoing email is not configured, an invitation SHALL give the admin the link to pass on, and a reset link SHALL be written to the server log. Neither SHALL be shown to an anonymous requester.

#### Scenario: Demo without SMTP
- **WHEN** an admin invites an account and email is not configured
- **THEN** the admin page shows the invitation link with a copy button

### Requirement: Usable on a phone and by keyboard
The forgot-password and set-password pages SHALL start below the header, have no sideways scroll at 360px, label every field, and show each error next to its field.

#### Scenario: Phone
- **WHEN** a person opens a reset link on a 360px phone
- **THEN** the form is readable and usable without scrolling sideways
