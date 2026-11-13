# Design

## Context

- `lead` has `intent` (price | appointment | handoff), `request`, `conversation`, `contact` (free text) and `status` (default `new`). Only `pipeline/assistant.py::_create_lead` writes it, called from `respond()` for `/chat`. `GET /leads` (`sales` plus approvers) lists it, and `LeadsView.vue` renders chat-only fields.
- Behaviour: `phien_truy_cap` gets a row only after the visitor accepted the banner. `su_kien` stores `xem_khong_gian` events with a `gia_tri` snapshot (`dimension:value`). The browser keeps the session id in `sessionStorage` (`d3_phien`) and the banner answer in `localStorage` (`consent.get()` = `yes` / `no`). The banner text names the purpose as "hiểu điều khách quan tâm và cải thiện bộ lọc", which does not cover giving a consultant one's own viewing history.
- Projects (`/du-an/<slug>`) are static frontend data (`src/assets/projects/<slug>/`), not database rows. Spaces are database rows.
- `schema.sql` is mounted into the Postgres init directory, so it runs only on a fresh volume. It is written idempotently (`IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS`). The current dev database already exists.
- There is no outgoing mail anywhere in the backend. `ratelimit.limit(name, count, seconds)` is an in-memory per-IP dependency.

## Goals / Non-Goals

**Goals:**
- One intake function that every source calls, so the brief (UC08) and the estimate (UC10) later add only a `nguon` value and their own payload.
- Leads must work in the demo with zero new configuration, so mail is optional.

**Non-Goals:**
- No queue or worker for notifications. SMTP is sent inline in a FastAPI background task.
- No change to the consent banner and no new event types. Project-page views are not tracked yet, so the profile is built from space views only.
- No deduplication of repeat submissions from the same phone.

## Decisions

### 1. Extend `lead` rather than add a `khach_tiem_nang` table
The class diagram's `KhachTiemNang` (ho_ten, so_dien_thoai, email, nguon, tom_tat_so_thich, ma_phien) maps onto the existing table. Columns are added with Vietnamese names to match `class-6` and the taxonomy and behaviour tables: `nguon`, `ho_ten`, `so_dien_thoai`, `email`, `loi_nhan`, `ngu_canh jsonb`, `ho_so_hanh_vi jsonb` (= `tom_tat_so_thich`), and `phien_id text REFERENCES phien_truy_cap ON DELETE SET NULL`. `intent` drops `NOT NULL`. `contact` stays for chat (free text). A backfill sets `nguon = 'chat'` where it is null, then `nguon` gets `NOT NULL DEFAULT 'form'` with a CHECK of `form | chat | brief | estimate`.
- *Alternative:* a new table plus a view for the old one. Rejected because it gives two sources of truth for `/khach-hang` and a bigger migration for no gain.
- `ON DELETE SET NULL` on `phien_id` keeps the lead when a visitor's behaviour data is deleted (act-7 delete request, future). The profile is a snapshot, so the lead keeps what was consented at the time.

### 2. Profile is a snapshot built at intake
`pipeline/leads.py::behaviour_profile(phien_id)` reads that session's `su_kien` (newest 12 distinct spaces) and counts `gia_tri` across all its events. It returns `{"spaces": [{id, relative_path, space_type, design_style}], "top": [["design_style:Wabi_sabi", 3], ...] (≤5), "views": n}`. A summary line ("Wabi_sabi 60% · phòng khách · 4 không gian") is derived from it for the email and the list.
- It is stored on the lead and not recomputed, so a later taxonomy merge or a session delete does not change what the consultant saw (the same rule as `SuKien.cac_gia_tri_phan_loai`).
- Server-side consent check: a profile is attached only if `gui_ho_so` is true **and** a `phien_truy_cap` row exists for the id. That row exists only after banner consent. Otherwise `phien_id` is not stored at all.

### 3. Second opt-in on the form, not a banner change
Sharing one's own history with a consultant is a different purpose from aggregate analytics (NĐ13/2023 purpose limitation), so it gets its own unticked box at the point of use. That box is shown only when the banner answer is `yes`.
- *Alternative:* extend the banner text to cover it. Rejected because a pre-given, bundled consent is weaker, and it would touch the banner the whole site depends on.

### 4. Anti-spam: rate limit + honeypot + fill time, no CAPTCHA
`limit("leads", 5, 600)`. The form has a hidden `website` field and sends `t_ms` (ms since the form mounted). Filled honeypot or `t_ms < 3000` → return the normal 201 shape with `lead_id: null` and store nothing (bots get no signal). The fill time is client-reported, which is enough against naive bots. That is the threat for a portfolio site.
- *Alternative:* reCAPTCHA or Turnstile. Rejected because it needs third-party keys, adds a privacy notice, and makes the demo harder.

### 5. Validation in the Pydantic model, normalised phone
`LeadIn`: `ho_ten` 1–100 chars after strip, `so_dien_thoai` normalised by removing spaces, dots and dashes, `+84` → `0`, then `^0\d{9}$`, `email` optional (simple regex, ≤ 200), `loi_nhan` ≤ 1000, `trang` (≤ 200, starts with `/`), `du_an` (slug pattern, ≤ 100), `space_id` (int, optional), `phien_id` (same pattern as `/events`), `gui_ho_so` bool, `website`, `t_ms`. Errors return FastAPI's 422 shape. The form maps `loc[-1]` to the field and shows a Vietnamese message from a small client table, so the server messages stay stable codes.
- The project slug is not checked against a list, because projects live in the frontend. The leads page links it as `/du-an/<slug>`, and an unknown slug shows the page's own "Không tìm thấy dự án".

### 6. Notification: SMTP if configured, else log; sent after the response
`pipeline/notify.py` uses stdlib `smtplib` + `email.message`. Config: `D3_SMTP_HOST`, `D3_SMTP_PORT` (587, STARTTLS), `D3_SMTP_USER`, `D3_SMTP_PASSWORD`, `D3_SMTP_FROM`, and `D3_SALES_EMAIL`. Without host or sales address, it does `logging.info("lead %s: ...")`. The endpoint schedules it with `BackgroundTasks`, so a slow or failing mail server never delays or fails the visitor's request. Failures are logged with the lead id. The chat path calls the same `notify_new_lead` through a background task added in `/chat`.
- The visitor confirmation goes out only when an email was given and SMTP is configured. It has a plain-text body and no profile.
- *Alternative:* a notifications table plus a badge. Deferred, because the existing `status = 'new'` already marks unseen leads on `/khach-hang`.

### 7. Chat moves onto the intake
`respond()` keeps deciding *whether* a lead is needed (intent). It calls `leads.create_lead(nguon="chat", intent=..., request=..., conversation=..., contact=..., phien_id=..., gui_ho_so=...)`. `Chat` gains optional `phien_id` and `gui_ho_so`. ChatWidget shows the same opt-in box under its contact field when consent is `yes`.

### 8. Frontend
- `ContactForm.vue` props are `{ project?: string, spaceId?: number, title?: string }`. It reads `consent.get()` and `visitId()` from `api.js`. It validates client-side with the same regexes, then calls `createLead(...)`. It renders the form, then a `role="status"` confirmation. Errors use `aria-describedby` and `role="alert"`. It uses `type="tel"` with `inputmode="tel"`, and `type="email"`. It uses only existing design tokens and classes (`btn`, `small`, form styles from the chat and login pages).
- `ProjectView.vue` places `<section class="pv-contact">` with `<ContactForm :project="project.slug" title="Tư vấn về dự án này" />` between the gallery and `pv-nav`.
- `LeadsView.vue` gets a source chip (`Form liên hệ` / `Trợ lý chat` / …), the name, phone (`tel:` link) and email (`mailto:`), the message, a context link (`/du-an/<slug>` or `/khong-gian/<id>`), and the profile summary with a `<details>` of thumbnail links. The chat block stays as it is. A source filter uses the existing chip style.

## Risks / Trade-offs

- [The fill-time check is client-reported] → Accepted. The rate limit still bounds abuse, and stronger checks can be added behind the same response shape.
- [The in-memory rate limit is per process] → This is already the case for `/chat` and `/auth`, and is noted in `ratelimit.py`. Behind nginx the visitors do not share one bucket, because uvicorn runs with `--proxy-headers --forwarded-allow-ips *` and so `request.client` is already the visitor's IP (checked in task 2.4). The flip side, which existed before this change: since every peer is trusted, a caller can send a fresh `X-Forwarded-For` per request and dodge every limiter. → Out of scope here. The fix is to narrow `--forwarded-allow-ips` to the nginx container's network and stop publishing port 8001 outside development, done for all limiters at once in a separate change.
- [The existing DB does not get schema changes automatically] → Apply `schema.sql` by hand (see Migration). Every statement is idempotent.
- [Personal data in emails and logs] → The log line holds only the lead id, source and profile summary, not the phone or email. Emails go only to the configured sales address and to the visitor themself.
- [The profile only reflects space pages, not `/du-an` pages] → Accepted for now. A later change can add a `xem_du_an` event type, and the profile function will pick it up.

## Migration Plan

1. Append the idempotent `ALTER TABLE lead ...` block and the backfill to `backend/schema.sql`.
2. On an existing database: `docker compose exec -T db psql -U d3 -d d3 < backend/schema.sql`. On a fresh volume it runs automatically.
3. Deploy the backend, then the frontend. The old frontend keeps working, because `GET /leads` only gains fields and `/chat` accepts the old body.
4. Rollback: redeploy the previous code. The extra columns are nullable or defaulted, so the old code ignores them.

## Open Questions

- Which mailbox is the real sales address, and which SMTP account sends it? This only fills in env vars and does not change the code.
