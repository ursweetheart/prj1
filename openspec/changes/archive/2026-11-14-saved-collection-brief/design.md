# Design

## Context

- **Lead intake** (`backend/pipeline/leads.py`): `create_lead(nguon, ...)` already accepts `request` (jsonb) and applies the double-consent behaviour profile. `notify.notify_new_lead` / `confirm_to_visitor` send mail when SMTP is configured, else log. `POST /leads` has the validation (`LeadIn`: VN phone, email, honeypot `website`, `t_ms`), and `limit("leads", 5, 600)`. `lead.nguon` already allows `brief`.
- **Spaces UI (Tùng, `space-explorer`):** `SpaceTile.vue` is a single `<router-link>` card. `SpaceView.vue` has a title row and a side panel. The "Không gian" menu item shows only when `ai.state === 'on'` (`src/lib/projectSpaces.js`).
- **Auth:** JWT in localStorage. `loadUser()` runs at start (`src/main.js`), after `login()`, after `register()` (which logs in), and after an OAuth return (`adoptTokenFromHash()` then `loadUser()`). `session.user` is reactive.
- **Data:** `GET /spaces` has no id filter. Tags live in `space_gia_tri` → `gia_tri_phan_loai` → `chieu_phan_loai` (`phong_cach`, `tong_mau`, `khong_gian`, …). Labels such as "Ấm" and "Phòng khách" come from `gia_tri_phan_loai.ten`.
- **Class diagram (`class-6`):** `BoSuuTap(ma, ma_nguoi_dung, ma_phien_neu_chua_dang_nhap, ten, ma_chia_se, ngay_tao)`, n–n with `Anh`, and `KhachTiemNang.ma_bo_suu_tap`.

## Goals / Non-Goals

**Goals:**
- One path for sending a brief, whether the visitor is signed in or not.
- The lead keeps exactly what was sent, so later edits never rewrite history.
- No new dependencies; the stack stays the same.

**Non-Goals:**
- Server-side collections for anonymous visitors. `ma_phien_neu_chua_dang_nhap` from the class diagram is not used, because act-8 keeps that case in the browser.
- Multiple named collections, renaming (`ten`), and editable public sharing.

## Decisions

### 1. Two tables; a sent brief is its own frozen row
```
bo_suu_tap      id, nguoi_dung_id -> app_user (NULL for a sent copy of an anonymous visitor),
                loai 'dang_luu' | 'da_gui', ma_chia_se (unique, only on 'da_gui'), tom_tat jsonb, created_at
bo_suu_tap_anh  bo_suu_tap_id -> bo_suu_tap ON DELETE CASCADE, space_id -> space ON DELETE CASCADE,
                ghi_chu text, created_at,  PRIMARY KEY (bo_suu_tap_id, space_id)
lead            + bo_suu_tap_id -> bo_suu_tap ON DELETE SET NULL
```
A partial unique index on `(nguoi_dung_id) WHERE loai = 'dang_luu'` gives one working collection per account. Sending a brief always inserts a new `da_gui` row with copies of the items and a `ma_chia_se`, so a sent brief never changes (spec "Brief keeps the photos as sent"), and the working collection is untouched.
- *Alternative:* point the lead at the live account collection. Rejected: the consultant would see photos change under them, and anonymous visitors have no server collection to point at.
- `ma_chia_se = secrets.token_urlsafe(12)` (16 URL-safe characters, 96 bits).

### 2. Anonymous collection in localStorage; the account is the source of truth once signed in
`src/lib/collection.js` is a reactive store: `items: [{space_id, ghi_chu, t}]`, plus `has(id)`, `toggle(id)`, `setNote(id, text)`, `remove(id)`, `count`. A watcher on `session.user` switches its mode:
- no user → read and write `localStorage['d3_bo_suu_tap']`, guarded in try/catch (memory-only if storage is blocked);
- user, browser empty → `GET /collections/me`;
- user, browser holds items → `POST /collections/me/merge` with them, then clear the key, then use the returned items.

This covers email sign-in, sign-up and OAuth through the one `session.user` change, with no edits to `LoginView` or `auth.py`. Writes in account mode are optimistic, rolled back with an error message on failure.

### 3. API
| Method | Path | Who | Notes |
| :-- | :-- | :-- | :-- |
| GET | `/collections/me` | signed in | `[{space_id, ghi_chu, created_at}]`; unpublished spaces filtered out |
| PUT | `/collections/me/items/{space_id}` | signed in | body `{ghi_chu?}`: add or update; 404 if not published; 409 `bo_suu_tap_day` at 60 |
| DELETE | `/collections/me/items/{space_id}` | signed in | 204 |
| POST | `/collections/me/merge` | signed in | body `{items:[{space_id, ghi_chu}]}` (≤ 60): adds missing; an empty account note takes the browser note; caps at 60; returns items |
| GET | `/collections/shared/{ma}` | public | the `da_gui` copy: items with space fields and notes, `tom_tat`, `created_at`; no contact data; 404 otherwise |
| POST | `/briefs` | public | see 4; 201 `{lead_id, ma_chia_se, message}` |
| GET | `/spaces?ids=1,2,3` | public | new optional filter (≤ 60 ids) so the browser collection can show its photos in one call; same published-only rule |

The collection endpoints use `require(*ROLES)`, so any signed-in role (staff can save too), with `limit("collections", 120, 60)`. `/briefs` shares `limit("leads", 5, 600)` with `/leads`, because both create leads.

### 4. `POST /briefs` reuses the lead form model
`BriefIn(LeadIn)` keeps the contact validation, honeypot and `t_ms`. It adds `loai_nha` (the `loai_cong_trinh` codes plus `khac`), `dien_tich_m2` (10–5000, optional), `ngan_sach` (the `muc_dau_tu` codes plus `chua_ro`), and `items: [{space_id, ghi_chu ≤ 300}]` (1–60). `loi_nhan` serves as the brief note. The body's `items` is always what gets sent, for signed-in and anonymous visitors alike, because the client sends what it shows. The server keeps only published spaces and answers 422 `bo_suu_tap_trong` if none are left. Then, in one transaction, it does:
1. insert the `da_gui` copy with the items, the `ma_chia_se` and `tom_tat = brief_summary(ids)`;
2. `create_lead("brief", …, request={loai_nha, dien_tich_m2, ngan_sach, tom_tat}, bo_suu_tap_id=…)`, which keeps the double-consent profile rule;
3. schedule both notices (background tasks, as for `/leads`).

A bot trap (honeypot or a too-fast send) returns the normal 201 shape with `lead_id: null` and `ma_chia_se: null`, and nothing is stored.

### 5. Summary of the photos
`leads.brief_summary(space_ids)` counts tags over the sent photos (one count per photo per value) and ignores `*:khac`. It returns:
- the leading style (`phong_cach`) with its share of the photos;
- the leading tone (`tong_mau`), shown as "tông <ten>";
- up to 2 space types (`khong_gian`) that appear on at least 2 photos, or the only one when 1 photo is sent.

It is stored as `{top: {...}, n, line}`, with `line` as in the spec example. It differs from the behaviour profile on purpose: these are photos the visitor chose, so no behaviour consent is involved.

### 6. Notices
`notify_new_lead` adds the brief lines for `nguon = 'brief'`: house type, area and budget (with labels), `tom_tat.line`, and the share URL (`D3_FRONTEND_URL` + `bo-suu-tap/xem/<ma>`). `confirm_to_visitor` adds the share URL for briefs. Log lines still carry no phone or email.

### 7. Frontend pieces
- **`SaveHeart.vue`:** a `<button aria-pressed>` with an inline SVG heart, `aria-label` "Lưu vào / Bỏ khỏi bộ sưu tập", and a toast-free inline error (`role=alert`) for "đã đủ 60 ảnh".
- **`SpaceTile.vue`:** the card becomes a `<div class="space-tile">` holding the existing `router-link` and an absolutely-positioned `SaveHeart` over the photo corner. Its markup and classes stay the same otherwise, because a button inside a link would be invalid HTML.
- **`SpaceView.vue`:** a `SaveHeart` with its text label in the title row, next to the ‹ › links.
- **`CollectionView.vue`:**
  - `/bo-suu-tap`: the grid of saved spaces (`GET /spaces?ids=` in browser mode; account items joined the same way), a note `<textarea>` per photo saved on blur, remove, an empty state, the sign-up invitation when anonymous, and "Gửi cho kiến trúc sư" revealing `BriefForm`.
  - `/bo-suu-tap/xem/:ma`: the read-only shared view.
- **`BriefForm.vue`:** the `ContactForm` pattern (same validation helpers, honeypot, `t_ms`, opt-in box when consented, 422/429 handling), plus selects for house type and budget and a number field for area. On success it shows the confirmation with the share link and a "Sao chép link" button.
- **`SiteNav.vue`:** a "Bộ sưu tập" link in `nav-account`, shown when `ai.state === 'on'`, with " (n)" appended when n > 0.
- **`LeadsView.vue`:** a brief block and a "Bộ sưu tập" filter chip.

## Risks / Trade-offs

- [An anonymous collection is lost if the visitor clears site data or switches device] → That's the point of the sign-up invitation on the collection page. The data never leaves the browser until the visitor chooses.
- [The heart edits Tùng's `SpaceTile` and `SpaceView`] → The change is additive and the layout is kept. Tell him before merging, and check his `space-explorer` scenarios still pass (tile opens the space page, space page layout).
- [Each brief stores a copy (rows grow with briefs)] → At most 60 rows per brief. Briefs are rare compared with views, so this is negligible at this scale.
- [Share links are bearer links: anyone with the link sees the photos and notes] → The view carries no contact data, the code is unguessable, and the notes are the visitor's own words about photos. The form's notice says the collection link goes to the consultant.
- [Header space at narrow widths (navbar task 5.4)] → The link is short ("Bộ sưu tập (n)"). Check at 360px together with the open navbar task.

## Migration Plan

1. Append the idempotent block to `backend/schema.sql`: both tables, the partial unique index, and `ALTER TABLE lead ADD COLUMN IF NOT EXISTS bo_suu_tap_id`.
2. Apply it to the existing DB with `docker compose exec -T db psql -U d3 -d d3 < backend/schema.sql`.
3. Rebuild the backend and web. Rollback is to redeploy the previous code; the new tables are unused by it.
