# Proposal

## Why

UC24 is marked "Có (trừ mời / quên mật khẩu)". Seq-19 begins with steps that don't exist yet:
- step 1: the admin creates an account and picks its role;
- step 5: the server creates the user with that role;
- step 7: it sends an invitation to set a password;
- steps 10–11: the new user sets a password and signs in.

Today a staff member has to register as a visitor and be promoted afterwards. Nobody can recover a forgotten password; the only way is for someone to edit the database. Both gaps would show in any demo of the admin pages.

## What Changes

- **Invite an account** (admin, `/quan-tri/tai-khoan`): enter an email and a role; the account is created with that role and no password. An invitation link valid for **72 hours** is emailed.
  - The account list shows such accounts as **"Chưa kích hoạt"**. The admin can **resend** (a new link; older ones stop working) or **cancel** (the links stop working and the account is locked with the reason "Huỷ lời mời").
  - Inviting an email that already has an account is refused, with a pointer to change its role instead.
  - Every invite, resend and cancel goes into the account change log.
- **"Quên mật khẩu?"** on the sign-in page leads to `/quen-mat-khau`. A reset link valid for **1 hour** is emailed.
  - The page always answers the same way whether or not the email has an account, so it doesn't reveal which emails are registered.
  - No link is sent to a locked account or a placeholder address.
- **One page, `/dat-mat-khau`,** sets the password for both links. The link carries a random code in the URL's `#` part, so it isn't sent to the server in request logs or referrers.
  - The page says whether it's an invitation or a reset, and for which (partly hidden) email.
  - The new password follows the existing rule of 8–128 characters.
  - A successful submit signs the person in.
- **Links are single-use.** A used, expired, replaced or cancelled link is refused with a clear message and a way to ask for a new one. Only a hash of each code is stored.
- **A reset ends every other open session** of that account, using the same mechanism as locking.
- **Without email configured,** the invite answer gives the admin the link to copy and pass on, and a reset link is written to the backend log, the same as other notices. The demo still works.
- **Rate limits:**
  - "Quên mật khẩu": 5 per 10 minutes per IP;
  - setting a password: 10 per minute;
  - invitations: admin only.

## Capabilities

### New Capabilities
- `account-passwords`: password links (invitation and reset), their lifetime and single use, the "forgot password" request that reveals nothing, the set-password page, and ending other sessions after a reset.

### Modified Capabilities
- `account-admin`: added requirements for inviting an account with a role, showing not-yet-activated accounts, resending and cancelling an invitation, and logging all three. The existing requirements are unchanged.

## Impact

- **Backend:**
  - new `backend/pipeline/password_links.py` (create, hash, check, use, void);
  - `backend/pipeline/accounts.py` (invite, resend, cancel, with guards and log);
  - `backend/auth.py`:
    - `POST /users/invite`, `POST /users/{id}/invite/resend`, `POST /users/{id}/invite/cancel`;
    - `POST /auth/forgot`, `POST /auth/link-info`, `POST /auth/set-password`;
    - `GET /users` gains `chua_kich_hoat`;
  - `backend/pipeline/notify.py` (the two emails);
  - new `backend/tests/test_account_passwords.py`.
- **Schema:** a new table `ma_dat_mat_khau` (account, kind, code hash, expiry, used / voided time, created by).
- **Frontend (all ours):**
  - `src/api.js`;
  - `UsersView.vue` (the invite form, the "Chưa kích hoạt" badge, resend / cancel, and the copyable link when email is off);
  - `LoginView.vue` (the "Quên mật khẩu?" link);
  - new `ForgotPasswordView.vue` and `SetPasswordView.vue`;
  - two routes.
- **Out of scope:**
  - changing your password while signed in;
  - email verification for self-registration;
  - two-factor sign-in;
  - bulk invitations.
