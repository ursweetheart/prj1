# Proposal

## Why

Roles decide everything staff can do:
- architects upload and tag;
- content staff edit text and knowledge;
- sales see leads and trends;
- the lead architect approves;
- an admin manages.

Today a role is granted only by running `python set_role.py <email> <role>` inside the backend container, or by calling `PATCH /users/{id}/role` from Swagger. There is no list of accounts, no way to see who has which role, and no way to stop an account from signing in. A departing employee keeps their access as long as the site keeps refreshing their token (each lasts an hour and is renewed before it expires).

UC24 and seq-19 (steps 16–19) describe an admin who changes a role or locks an account from the admin screen, with the change logged and the account's open sessions ended. This is roadmap item 1.7.

## What Changes

- **`/quan-tri/tai-khoan`** (admin only), a list of accounts:
  - email, role, sign-in methods (password, Google, Facebook), created date, and whether the account is locked and why;
  - search by email, and filters by role and by locked/active.
- **Change a role** from the list, after a confirmation that names the old and new role. The new role applies on the account's next request; that is already how roles are read.
- **Lock an account** with a reason (3–300 characters), and **unlock** it.
  - A locked account cannot sign in with a password, Google or Facebook, and its open sessions stop working on their next request.
  - Unlocking does not bring back the old sessions; the person signs in again.
- **Guards:**
  - an admin cannot change their own role or lock themselves;
  - the last active admin cannot be demoted or locked.

  The screen explains why the control is disabled, and the server refuses with 409.
- **Every role change, lock and unlock is logged** (who, whom, before → after, reason). The 20 most recent are shown under the list.
- **Sign-in messages:** the sign-in page says "Tài khoản đã bị khoá" (account locked) instead of the generic error.
- **The staff menu** gets "Tài khoản" for admins.
- `set_role.py` stays for creating the first admin and is documented as that bootstrap step.

## Capabilities

### New Capabilities
- `account-admin`: listing accounts, changing roles, locking and unlocking with revocation of open sessions, the self and last-admin guards, and the account change log.

### Modified Capabilities
None. No main spec covers sign-in or roles yet.

## Impact

- **Backend:**
  - `backend/schema.sql`:
    - `app_user` adds `bi_khoa`, `ly_do_khoa` and `phien_tu` (sessions issued before this are invalid);
    - a new table `nhat_ky_tai_khoan`.
  - `backend/auth.py`:
    - tokens carry `iat`;
    - `optional_user` rejects locked accounts and revoked sessions with 401;
    - `/auth/login`, `/auth/refresh` and the Google and Facebook callbacks refuse locked accounts;
    - `PATCH /users/{id}/role` gets the guards and the log;
    - new `GET /users`, `POST /users/{id}/lock` and `POST /users/{id}/unlock`.
  - New tests in `backend/tests/test_user_admin.py`.
- **Frontend:**
  - `src/api.js`: the calls, and the locked message on sign-in;
  - new `src/views/UsersView.vue`;
  - `src/router/index.js`;
  - `src/components/SiteNav.vue`;
  - `src/views/LoginView.vue`: the locked message from an OAuth redirect.
- **Assumptions recorded here:**
  - **No invitations.** seq-19 steps 1–11 (the admin creates an account, an email invites the person to set a password) need the same email and set-password flow as a password reset, which this change leaves out. Staff sign up themselves, as today, and the admin then gives them a role.
  - **A role change does not sign the person out**, unlike step 19 for role changes. The role is read from the database on every request, so it already applies at once. Only locking ends sessions.
- **Out of scope:**
  - invitations;
  - password reset;
  - deleting accounts;
  - showing when an account was last active (not tracked today).
