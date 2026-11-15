# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.

Tests use throw-away `@example.com` accounts, removed afterwards.

## 1. Backend

- [x] 1.1 Make these changes:
  - in `backend/schema.sql`, add `app_user.bi_khoa`, `ly_do_khoa` and `phien_tu`, and the table `nhat_ky_tai_khoan`, then re-apply;
  - in `auth.py`:
    - `make_token` adds `iat`;
    - `optional_user` rejects locked accounts and tokens issued before `phien_tu` with 401;
    - `/auth/login` answers 403 with the locked message after a correct password;
    - `_signed_in` refuses locked accounts (`#loi=tai_khoan_bi_khoa` redirect, or 403).

  Verify with tests in `tests/test_user_admin.py`:
  - a token stops working right after its account is locked;
  - a locked account's correct password gives 403, and a wrong one gives 401;
  - after unlocking, a fresh sign-in works and the pre-lock token is still refused;
  - a token without `iat` works until a lock;
  - `/auth/refresh` on a locked account gives 401;
  - `_signed_in` for a locked account gives the redirect or 403;
  - `tests/test_auth.py` keeps passing apart from its 3 known OAuth failures.
- [x] 1.2 Create `backend/pipeline/accounts.py` with `list_accounts`, `change_role`, `lock`, `unlock` and `recent`. It applies the self and last-active-admin guards with admin rows locked, and writes a log row per change. Make `set_role.py` log too.

  Verify with tests:
  - an admin demoting or locking themselves gets a conflict;
  - the last active admin cannot be demoted or locked by another admin;
  - with two admins one can be demoted;
  - a locked admin does not count as active;
  - the list carries `dang_nhap`, `bi_khoa`, `la_toi`, `khoa_duoc` / `doi_vai_tro_duoc` with reasons, and never `password_hash`, `google_sub` or `facebook_id`;
  - search and filters work;
  - every change logs one row with its before, after and reason.
- [x] 1.3 Add `GET /users`, the guarded and logged `PATCH /users/{id}/role`, `POST /users/{id}/lock` and `POST /users/{id}/unlock` (admin only).

  Verify with API tests:
  - lead_architect gets 403, anonymous 401;
  - an unknown role or an empty reason gives 422;
  - an unknown id gives 404;
  - a guard gives 409 with its reason;
  - a promoted visitor can open a sales endpoint on the next request with the same token.

## 2. Frontend

- [x] 2.1 In `src/api.js`, add `listUsers`, `setUserRole`, `lockUser` and `unlockUser`, and show the server message for a 403 on `login()`. In `LoginView.vue`, show the locked message from `#loi=tai_khoan_bi_khoa`. Create `UsersView.vue` (search, role filter, status chips, table or cards, role select with a confirm dialog, lock dialog with a reason, unlock, disabled controls with reasons, "Gần đây"). Add the route (admin) and "Tài khoản" in `SiteNav.vue`.

  Verify in the browser with a throw-away admin and accounts:
  - change a visitor to sales after confirming, and cancelling restores the select;
  - lock an architect with a reason, and that architect's open tab is signed out on its next action, and signing in shows "Tài khoản đã bị khoá";
  - unlock, and signing in works again;
  - the admin's own row shows its controls as disabled with the reason;
  - search and filters work;
  - "Gần đây" lists the changes;
  - keyboard only works;
  - 360px has no sideways scroll;
  - a lead_architect sees no "Tài khoản" link and is redirected.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - UC24 / seq-19 status;
  - roadmap 1.7;
  - the API table;
  - the columns and table;
  - the accounts section: `set_role.py` creates the first admin, and the rest is done at `/quan-tri/tai-khoan`.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
