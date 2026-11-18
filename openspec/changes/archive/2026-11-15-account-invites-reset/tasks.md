# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Schema:** re-apply it with `docker compose exec -T db psql -U d3 -d d3 -q -v ON_ERROR_STOP=1 < backend/schema.sql`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.
- **Tests never send real mail:** `notify._send` is monkeypatched to collect messages, and the SMTP settings are set or cleared per test.
- **Throw-away accounts:** they use `@example.com` and are removed afterwards. The register and forgot rate limits are reset between tests.

## 1. Backend

- [x] 1.1 Schema: add table `ma_dat_mat_khau`, as in the design.

  Verify that `schema.sql` applies twice without errors.
- [x] 1.2 Create `backend/pipeline/password_links.py` (`issue`, `check`, `use`, `link_url`, masked email).

  Verify with tests:
  - an invite link expires after 72 h and a reset link after 1 h (rows aged in SQL);
  - a second `issue` voids the first;
  - `use` sets a password that logs in, marks the link used, and a second `use` fails with `da_dung`;
  - a reset sets `phien_tu`, so a token from before it gets 401 and the new token works;
  - a locked account's link fails with `khoa`;
  - only the hash is stored: the code appears nowhere in the table.
- [x] 1.3 Invitations in `accounts.py` and the endpoints `POST /users/invite`, `/users/{id}/invite/resend` and `/users/{id}/invite/cancel`; `chua_kich_hoat` and `moi_luc` in `GET /users`.

  Verify with API tests:
  - an admin invite creates the account with the role and no password, it lists as `chua_kich_hoat`, and the invitation mail is collected (SMTP set) or `link` is returned (SMTP unset);
  - an existing email gives 409;
  - non-admins get 403, and anonymous 401;
  - resend voids the old link; cancel voids it and locks with "Huỷ lời mời";
  - resend or cancel on an active account gives 409;
  - the log has `moi`, `gui_lai_moi` and `huy_moi`.
- [x] 1.4 `POST /auth/forgot`, `POST /auth/link-info` and `POST /auth/set-password`, with the reset email and log.

  Verify with API tests:
  - forgot gives the same status and body for an existing, an unknown, a locked and a `.invalid` account, and a mail is collected only for the existing one;
  - the 6th request in 10 minutes gives 429;
  - `link-info` gives the kind and the hidden email, or 410 with the reason;
  - set-password with a 7-character password gives 422;
  - a valid one returns a token whose `/auth/me` has the invited role;
  - an invited account is no longer `chua_kich_hoat` afterwards;
  - the code never appears in a query string.

## 2. Frontend

- [x] 2.1 `src/api.js` helpers. In `UsersView.vue`:
  - the invite form;
  - the "Chưa kích hoạt" badge with resend / cancel;
  - the copyable link when email is off.

  Add the "Quên mật khẩu?" link to `LoginView.vue`. Create `ForgotPasswordView.vue` and `SetPasswordView.vue` and their routes.

  Verify in the browser, SMTP unset:
  - **invite:** the admin invites an architect and copies the shown link; opening it in a fresh browser shows "Kích hoạt tài khoản" with the hidden email, and the hash is gone from the address bar; setting a password signs them in as an architect;
  - **reuse:** opening the link again shows "đã được sử dụng" with a link to "Quên mật khẩu";
  - **forgot:** it shows the same message for a real and a made-up email;
  - **reset:** the reset link from the backend log sets a new password, and the old session on another browser context is signed out on its next request;
  - **resend and cancel** update the list;
  - **keyboard:** errors show at the field, and all pages work by keyboard;
  - **360px:** no sideways scroll on the three pages.

  Remove the test accounts afterwards.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - UC24;
  - seq-19 (steps 1–11 now done);
  - roadmap 1.7's remaining item;
  - the API table;
  - the setup note (invite links without SMTP, the reset link in the log, and that production needs SMTP).

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
