# account-admin Specification

## Purpose
Lets an admin see every account, give each the right role, and stop an account from signing in (UC24, seq-19), with every change logged and without ever leaving the site without an admin.

## Requirements

### Requirement: Only admins manage accounts
Listing accounts, changing roles, locking and unlocking SHALL be limited to the admin role. Other signed-in users SHALL get 403 and anonymous requests 401.

#### Scenario: Lead architect tries
- **WHEN** a lead architect requests the account list or changes a role
- **THEN** the server answers 403

### Requirement: Account list
The admin screen at `/quan-tri/tai-khoan` SHALL list every account with its email, role, sign-in methods (password, Google, Facebook), the date it was created, and whether it is locked with the reason. It SHALL allow searching by email and filtering by role and by locked or active. Password hashes and provider ids SHALL never be sent.

#### Scenario: Find a sales account
- **WHEN** an admin types "sales" in the search box and picks the role "sales"
- **THEN** only accounts whose email contains "sales" and whose role is sales are listed

#### Scenario: No secrets
- **WHEN** the account list is returned
- **THEN** it contains no password hash, Google subject or Facebook id, only whether each method is set up

### Requirement: Change a role
An admin SHALL be able to change an account's role to any of visitor, architect, content, sales, lead_architect or admin, after a confirmation that names the account, the old role and the new role. The new role SHALL apply to that account's next request without signing it out.

#### Scenario: Promote to sales
- **WHEN** an admin changes a visitor account to sales and confirms
- **THEN** that person's next request is allowed into `/khach-hang` data, and they stay signed in

### Requirement: Lock and unlock
An admin SHALL be able to lock an account with a reason of 3 to 300 characters, and to unlock it. A locked account SHALL NOT sign in with a password, Google or Facebook, and every token issued to it before the lock SHALL be refused on its next request. Unlocking SHALL NOT revive tokens issued before the lock.

#### Scenario: Lock a departing employee
- **WHEN** an admin locks an architect account with the reason "Nghỉ việc"
- **THEN** the architect's open session gets 401 on its next request and the site signs them out, and signing in again with their password answers 403 "Tài khoản đã bị khoá"

#### Scenario: Unlock
- **WHEN** the admin unlocks that account
- **THEN** the architect can sign in again, and the token from before the lock is still refused

### Requirement: Nobody locks the admins out
An admin SHALL NOT change their own role or lock their own account. The last active (unlocked) admin SHALL NOT be demoted or locked. The server SHALL answer 409 with a reason, and the screen SHALL show the control as unavailable with that reason.

#### Scenario: Self-demotion
- **WHEN** an admin tries to change their own role to lead_architect
- **THEN** the server answers 409 and the role stays admin

#### Scenario: Last admin
- **WHEN** there is one active admin and another admin tries to lock them
- **THEN** the server answers 409, because that would leave no active admin

### Requirement: Account change log
Every role change, lock and unlock SHALL be recorded with the admin who made it, the account, the time, the value before and after, and the lock reason. The screen SHALL show the 20 most recent changes.

#### Scenario: Log after a lock
- **WHEN** an admin locks an account
- **THEN** "Gần đây" lists the lock with the admin's email, the account's email, the time and the reason

### Requirement: Usable on a phone and by keyboard
The account screen SHALL be usable at 360px without sideways page scroll. Every action SHALL be reachable by keyboard, and its confirmation dialog SHALL return focus to the control that opened it when cancelled.

#### Scenario: Phone
- **WHEN** an admin opens `/quan-tri/tai-khoan` on a 360px screen
- **THEN** each account's email, role and status are readable and the page does not scroll sideways
