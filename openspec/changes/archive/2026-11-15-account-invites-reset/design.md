# Design

## Context

- **`app_user`** has `email` (unique, lowercase), `password_hash` (NULL for Google-only accounts), `google_sub`, `facebook_id`, `role`, `bi_khoa`, `ly_do_khoa` and `phien_tu`. A token whose `iat` is before `phien_tu` is refused, which is how locking ends sessions. Facebook-only accounts have `facebook-<id>@facebook.invalid`.
- **`auth.py`** (ours) holds register / login (pwdlib Argon2, rate-limited), `/users` admin endpoints that call `pipeline/accounts.py` (guards and `nhat_ky_tai_khoan` log) and the Google / Facebook flows.
  - Google links to an existing account by email and drops its password: an invited person who signs in with Google takes over the account, which is fine because Google verified the email.
- **`notify._send` / `_smtp_ready`** handle email. Notices are logged when SMTP is unset. `D3_FRONTEND_URL` is the site base for links.
- **Pages:** `LoginView.vue` and `UsersView.vue` are ours. Pages use `.page-top`.

## Goals / Non-Goals

**Goals:**
- Admin invitations as seq-19 draws them.
- Self-service reset.
- Short-lived, single-use links that are stored hashed.
- Nothing revealed to strangers.
- A working demo without SMTP.

**Non-Goals:**
- Changing your password while signed in.
- Email verification for self-registration.
- Two-factor sign-in.
- Bulk invites.

## Decisions

### 1. Table `ma_dat_mat_khau`
```sql
CREATE TABLE IF NOT EXISTS ma_dat_mat_khau (
  id serial PRIMARY KEY,
  tai_khoan_id int NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  loai text NOT NULL CHECK (loai IN ('moi', 'dat_lai')),
  ma_bam text NOT NULL UNIQUE,          -- sha256 hex of the code; the code itself is never stored
  het_han timestamptz NOT NULL,
  da_dung timestamptz,                  -- used
  da_huy timestamptz,                   -- replaced or cancelled
  tao_boi int REFERENCES app_user(id) ON DELETE SET NULL,   -- admin for invitations, NULL for self-service reset
  created_at timestamptz NOT NULL DEFAULT now()
);
```
- **The code** is `secrets.token_urlsafe(32)`, about 256 bits. A random code is hashed with SHA-256; a slow hash isn't needed for that.
- **"Active"** means `da_dung IS NULL AND da_huy IS NULL AND het_han > now()`.
- **Issuing a link** first sets `da_huy = now()` on the account's other active links.

### 2. `pipeline/password_links.py`
- `issue(conn, user_id, loai, by=None) -> code`: voids the others, then inserts with `het_han` (72 h for `moi`, 1 h for `dat_lai`).
- `check(conn, code) -> {id, user_id, loai, email}`: raises `LinkError(reason)` where reason is `khong_hop_le`, `het_han`, `da_dung`, `da_huy` or `khoa`. `khoa` means the account is locked.
- `use(conn, code, new_password) -> user_id`: checks again under `FOR UPDATE`, then:
  - sets `password_hash`;
  - marks the link `da_dung`;
  - voids the account's other links;
  - for `dat_lai`, sets `phien_tu = clock_timestamp()`, which ends earlier sessions; the new token issued after it is valid.
- `link_url(code)`: `D3_FRONTEND_URL` + `dat-mat-khau#ma=<code>`.
- **Masked email:** the first character, `***`, then `@domain`.

### 3. Invitations in `pipeline/accounts.py`
- **`invite(conn, admin, email, role)`:**
  - lowercases the email and validates the role;
  - 409 if any account has that email;
  - inserts `app_user (email, role)` with no password;
  - logs `moi` with `sau = {role}`;
  - returns the user and a code.
- **`pending(row)`:** true when `password_hash IS NULL AND google_sub IS NULL AND facebook_id IS NULL` and an invitation link exists for the account.
- **`resend(conn, admin, user_id)`:** 409 unless pending; issues a new link; logs `gui_lai_moi`.
- **`cancel(conn, admin, user_id)`:** 409 unless pending; voids the links; sets `bi_khoa = true, ly_do_khoa = 'Huỷ lời mời'`; logs `huy_moi`. The account stays, so the log keeps its history. The admin can unlock and resend later.
- **Guards:** inviting as admin is allowed, but the existing last-admin rules don't apply until the account is active.
- **`list_accounts`** adds `chua_kich_hoat` and `moi_luc`, the last invitation time.

### 4. Endpoints (`auth.py`)
| Endpoint | Who | Answer |
| :-- | :-- | :-- |
| `POST /users/invite {email, role}` | admin | 201 `{user, gui_email: bool, link?}`. `link` is only present when SMTP is not configured, so the admin can pass it on |
| `POST /users/{id}/invite/resend` | admin | same shape |
| `POST /users/{id}/invite/cancel` | admin | `{user}` |
| `POST /auth/forgot {email}` | public, 5 / 10 min | always 202 `{message}`; sends (or logs) a link only for an existing, unlocked account without a `.invalid` email |
| `POST /auth/link-info {ma}` | public, 20/min | `{loai, email_an}`, or 410 `{ly_do}` |
| `POST /auth/set-password {ma, mat_khau}` | public, 10/min | `{access_token}`; 410 `{ly_do}`; 422 for the password length |

- **The code travels in the request body,** never in the URL, so it stays out of access logs.
- **Same answer for every case:** `/auth/forgot` gives the same body and roughly the same time whether or not the account exists. Sending happens in a background task, so timing doesn't leak either.

### 5. Emails (`notify.py`)
- **Invitation:** "D3 Studio mời bạn tham gia với vai trò …", with the link and its 72-hour validity.
- **Reset:** the link, its 1-hour validity, and "Nếu không phải bạn yêu cầu, hãy bỏ qua thư này".
- **Without SMTP:** the invitation's link is returned to the admin, not logged. The reset link is logged (`d3.auth`) with the account id, the only way to test reset without mail. The doc says so, and the log is server-side only.

### 6. Pages
- **`LoginView.vue`:** a "Quên mật khẩu?" link under the password field, to `/quen-mat-khau`.
- **`ForgotPasswordView.vue`:** an email field, then the same confirmation message whatever happens; `page-top`.
- **`SetPasswordView.vue`:**
  - reads `#ma=`, then immediately clears the hash with `history.replaceState`, so the code doesn't stay in the address bar or history;
  - calls `link-info` and shows "Kích hoạt tài khoản" or "Đặt lại mật khẩu" with the hidden email;
  - has two password fields with the errors at the field;
  - on success, stores the token like the login does, loads the user and goes to `/quan-tri` for staff or `/` for visitors;
  - on a 410, shows the reason and a link to `/quen-mat-khau`.
- **`UsersView.vue`:**
  - a "Mời tài khoản" form (email, role select) above the list;
  - a "Chưa kích hoạt · mời lúc …" badge;
  - "Gửi lại lời mời" and "Huỷ lời mời" (with a confirmation);
  - when the answer has `link`, a notice with a read-only field and "Sao chép".

## Risks / Trade-offs

- **[A reset link in the server log without SMTP]** → Only when email isn't configured (dev or demo). It's documented, and the link lives an hour. Production must set SMTP.
- **[An email address alone receives the power to set a password]** → That's the standard for resets; the link is single-use and short-lived. The rate limit stops someone flooding an inbox.
- **[A cancelled invitation leaves a locked account]** → It's kept for the log. Unlock and resend reactivates it.
- **[Google sign-in on an invited email activates the account without the link]** → Acceptable, since Google verified the email. Its links are voided by the next `use`, or simply expire.

## Migration Plan

- Apply `schema.sql` (the new table) and rebuild the backend and web.
- **Rollback:** remove the endpoints and pages. Invited accounts without a password simply can't sign in by password.
