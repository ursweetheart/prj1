## ADDED Requirements

### Requirement: Invite an account with a role
An admin SHALL be able to invite an account by entering an email and a role. The account SHALL be created at once with that role and no password, and an invitation link SHALL be sent to the email. An email that already has an account SHALL be refused, with a pointer to change its role instead. Only admins SHALL invite; others SHALL get 403, and anonymous requests 401.

#### Scenario: Invite an architect
- **WHEN** the admin invites `kts.moi@example.com` as architect
- **THEN** the account exists with the role architect and no password, the list shows it as "Chưa kích hoạt", and an invitation is sent

#### Scenario: Existing email
- **WHEN** the admin invites an email that already has an account
- **THEN** the server answers 409 and no account or link is created

### Requirement: Not-yet-activated accounts
The account list SHALL mark accounts that were invited and have not set a password or signed in with Google or Facebook as "Chưa kích hoạt", with when the last invitation was sent. For such an account the admin SHALL be able to resend the invitation, which makes earlier links stop working, or cancel it, which makes every link stop working and locks the account with the reason "Huỷ lời mời". Resend and cancel SHALL be refused for an account that is already active.

#### Scenario: Resend
- **WHEN** the admin resends an invitation
- **THEN** a new link is sent, and the first link no longer works

#### Scenario: Cancel
- **WHEN** the admin cancels an invitation
- **THEN** the link no longer works and the account is locked with the reason "Huỷ lời mời"

### Requirement: Invitations are logged
Every invite, resend and cancel SHALL be written to the account change log, with the admin, the account, the role and the time.

#### Scenario: Log
- **WHEN** the admin invites an account and later resends the invitation
- **THEN** the change log shows both entries with the admin's email
