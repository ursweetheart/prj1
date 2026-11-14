# Design

## Context

- **Accounts.** `app_user (id, email UNIQUE, password_hash, google_sub UNIQUE, facebook_id UNIQUE, role CHECK in ROLES, created_at)`. Today one account exists, a lead architect, and no admin.
- **Tokens.** `make_token` signs `{"sub", "exp"}` (HS256, 7 days). `optional_user` decodes the token and reads `id, email, role` from the database on every request, so a role change already applies at once. `POST /auth/refresh` issues a fresh token for a valid one, and the client refreshes before expiry.
- **The client.** On any 401 with a token, `src/api.js` drops the token, which signs the user out.
- **Roles today.** `PATCH /users/{id}/role` (admin) validates the role and updates it, with no guards and no log. `set_role.py` does the same from a shell.
- **OAuth.** The Google and Facebook callbacks call `_signed_in(user_id)`, which redirects to `D3_FRONTEND_URL#token=…` or returns JSON.
- **Sign-in errors.** `login()` in `api.js` turns non-401 errors into "Không đăng nhập được (status)".

## Goals / Non-Goals

**Goals:**
- seq-19 steps 16–19, with an immediate effect on the affected account;
- no way to end up without an admin;
- an audit trail.

**Non-Goals:**
- invitations and password reset (they need an email and set-password flow);
- deleting accounts;
- last-seen tracking;
- per-session listing.

## Decisions

### 1. Revocation by a per-account cut-off, not a token blocklist
- **Tokens:** `make_token` adds `iat` with microseconds. JWT allows a fractional time, and whole seconds turned out to let a token issued in the lock's own second survive an unlock.
- **New columns:**
  - `phien_tu timestamptz`: tokens issued before it are invalid;
  - `bi_khoa boolean NOT NULL DEFAULT false`;
  - `ly_do_khoa text`.
- **`optional_user`** reads them with the role. It answers 401 when `bi_khoa` is set ("tài khoản đã bị khoá"), or when `phien_tu` is set and `iat < epoch(phien_tu)`. A token with no `iat` (issued before this change) counts as `iat = 0`, so it is cut off only once `phien_tu` exists.
- **Locking** sets `bi_khoa`, `ly_do_khoa` and `phien_tu = clock_timestamp()`. **Unlocking** clears `bi_khoa` and `ly_do_khoa` and keeps `phien_tu`, so the old tokens stay dead.
- **401, not 403:** a revoked session must be signed out, and the client signs out on 401.

Alternatives considered:
- *A table of revoked token ids.* It would need a `jti` on every token and a lookup that grows over time. One timestamp per account does the same job for "end every session of this account".
- *Revoking on a role change too* (seq-19 step 19 says "Đổi vai trò hoặc khóa"). Not needed: the role is read on every request. Signing someone out because they were promoted is only friction. This is recorded as a deliberate deviation.

### 2. Sign-in refuses locked accounts
- **`/auth/login`:** after a correct password, a locked account answers **403** `{"detail": "Tài khoản đã bị khoá. Liên hệ quản trị viên."}`. A wrong password still answers 401, so locking reveals nothing to someone who does not know the password.
- **`/auth/refresh`:** already fails through `optional_user` (401).
- **OAuth:** `_signed_in` checks the lock. With `D3_FRONTEND_URL` it redirects to `…/dang-nhap#loi=tai_khoan_bi_khoa`; without it, it answers 403 JSON.
- **The client:** `api.login()` shows the server's `detail` for 403. `LoginView` reads `#loi=tai_khoan_bi_khoa` once and shows the same message.

### 3. Guards in one place
`pipeline/accounts.py` holds:
- `list_accounts(conn, q, role, khoa)`;
- `change_role(conn, admin, user_id, role)`;
- `lock(conn, admin, user_id, reason)`;
- `unlock(conn, admin, user_id)`;
- `recent(conn)`.

The guards run inside the transaction, with the target row locked (`FOR UPDATE`):
- the target is the acting admin → `Conflict("không tự đổi vai trò / tự khoá")`;
- the target is an active admin, the action removes it from the active admins (demote or lock), and `count(active admins) = 1` → `Conflict("phải còn ít nhất một quản trị viên đang hoạt động")`.

Two admins demoting each other at the same moment could still both succeed, because each sees two admins. The count therefore locks all admin rows (`SELECT … WHERE role='admin' AND NOT bi_khoa FOR UPDATE`) before deciding.

### 4. List shape
Each item has:
- `id`, `email`, `role`, `created_at`;
- `dang_nhap`: a list from `mat_khau` / `google` / `facebook`, derived from which columns are non-null;
- `bi_khoa`, `ly_do_khoa`;
- `la_toi` (whether this is the acting admin);
- `khoa_duoc` / `doi_vai_tro_duoc` with a `ly_do_khong` reason (the guards, precomputed so the UI can disable the control and say why).

There is no pagination. Accounts number in the tens, and the list is capped at 500 with the search narrowing it. Facebook-only accounts have a placeholder email; it is shown as is, with the "Facebook" method marked.

### 5. Endpoints
All take `require("admin")`. Errors are 404, 409 (guard) and 422 (role or reason).

| Method | Path | Body or query | Answer |
| :-- | :-- | :-- | :-- |
| GET | `/users` | `?q=&role=&khoa=true\|false` | `{items, gan_day}` |
| PATCH | `/users/{id}/role` | `{role}` | the existing endpoint, now with guards and log |
| POST | `/users/{id}/lock` | `{ly_do}` | |
| POST | `/users/{id}/unlock` | | |

### 6. Log table
```sql
nhat_ky_tai_khoan (id serial, nguoi_dung_id int REFERENCES app_user ON DELETE SET NULL,  -- the admin
                   tai_khoan_id int REFERENCES app_user ON DELETE CASCADE,               -- the account
                   hanh_dong text,  -- doi_vai_tro | khoa | mo_khoa
                   truoc jsonb, sau jsonb, created_at timestamptz DEFAULT now())
```
`set_role.py` also writes a row, with `nguoi_dung_id NULL`, shown as "lệnh hệ thống".

### 7. Frontend
**`UsersView.vue`** at `/quan-tri/tai-khoan` (`meta.roles: ['admin']`, `page-top`):
- a search field, a role select, and status chips (Tất cả / Đang hoạt động / Bị khoá);
- **the list** is a table on wide screens and stacked cards below 760px. Each account shows:
  - the email (and "bạn" on the acting admin's own row);
  - sign-in method tags;
  - a role `<select>`;
  - the status;
  - "Khoá…" or "Mở khoá".
- **A role change** opens a confirm `<dialog>` ("Đổi vai trò của X từ A sang B?"). Cancelling resets the select and returns focus to it.
- **"Khoá…"** opens a dialog with a required reason (counter, error under the field).
- **Disabled controls** carry `aria-describedby` pointing at a short reason line.
- **"Gần đây"** lists the last 20 changes.

`SiteNav` adds `hasRole(['admin']) && { to: '/quan-tri/tai-khoan', label: 'Tài khoản' }`.

## Risks / Trade-offs

- **[The token clock]** The cut-off and `iat` come from the same host clock with microseconds. A token issued within the few milliseconds of the locking transaction could survive. → The lock check (`bi_khoa`) rejects it anyway while the account is locked; the window after an unlock is milliseconds wide.
- **[Tokens from before this change have no `iat`]** → They count as 0, so a lock (which sets `phien_tu`) cuts them off, and unlocked accounts are unaffected.
- **[One more read per request]** `optional_user` already reads the row, so this only adds two columns to the same query.
- **[No admin exists yet]** → `set_role.py you@example.com admin` remains the documented first step. The guards only ever prevent removing the last admin; they never block creating one.

## Migration Plan

- `schema.sql` (idempotent): the three columns on `app_user` and `nhat_ky_tai_khoan`. Re-apply it, then rebuild backend and web.
- Run `set_role.py` once to create the first admin, for example the demo account.
- **Rollback:** the columns are additive. Old code ignores `bi_khoa`, so locked accounts would get in again. Unlock or demote them before rolling back if that matters.
