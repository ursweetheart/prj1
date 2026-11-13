# Tasks

Tests run in the stack: `docker compose exec backend python -m pytest tests/<file> -q` (the DB needs at least one published space, which the 40 from roadmap 0.4 provide).

## 1. Data model

- [x] 1.1 Append the idempotent `lead` migration to `backend/schema.sql`. It adds the columns `nguon`, `ho_ten`, `so_dien_thoai`, `email`, `loi_nhan`, `ngu_canh jsonb`, `ho_so_hanh_vi jsonb` and `phien_id` (FK to `phien_truy_cap`, ON DELETE SET NULL), drops NOT NULL on `intent`, backfills `nguon='chat'`, then sets the `nguon` default to `'form'` with NOT NULL and the CHECK. Verify by running `docker compose exec -T db psql -U d3 -d d3 < backend/schema.sql` twice without errors, after which `\d lead` shows the columns and old rows have `nguon = 'chat'`.

## 2. Intake core (backend)

- [x] 2.1 Create `backend/pipeline/leads.py` with `behaviour_profile(phien_id)` (≤ 12 newest distinct spaces, top ≤ 5 `gia_tri` counts, total views) and `profile_summary(profile)`. Verify with `tests/test_leads.py::test_profile_*`: seed a session with 4 views (3 `Wabi_sabi`) and assert the order, the top value and the "… · 4 không gian" summary.
- [x] 2.2 Add `create_lead(nguon, *, ho_ten, so_dien_thoai, email, loi_nhan, ngu_canh, intent, request, conversation, contact, phien_id, gui_ho_so)` to `leads.py`. It attaches the profile and stores `phien_id` only when `gui_ho_so` is true and a `phien_truy_cap` row exists. Verify with tests: a declined session id gives no profile and a null `phien_id`, and an unticked box gives no profile.
- [x] 2.3 Create `backend/pipeline/notify.py`. `notify_new_lead(lead_id)` uses SMTP when `D3_SMTP_HOST` and `D3_SALES_EMAIL` are set, otherwise logs the id, source and summary with no phone or email. `confirm_to_visitor` sends only when an email exists and SMTP is configured. Exceptions are logged and never raised. Verify with tests that monkeypatch `smtplib.SMTP`: one message goes to sales with the summary, the visitor confirmation has no profile, a raising SMTP is only logged, and with no config `caplog` holds the id but not the phone.
- [x] 2.4 Check that visitors behind nginx get separate rate-limit buckets. Verify through `localhost:8080/api/leads`: requests with different `X-Forwarded-For` values are limited separately, and the 6th plain request gets a 429. Result: no code change was needed, because the backend `CMD` already runs uvicorn with `--proxy-headers --forwarded-allow-ips *`. A spoofed header also gets its own bucket (pre-existing, see design Risks).

## 3. Endpoints

- [x] 3.1 Add the `LeadIn` model and `POST /leads` (201, `limit("leads", 5, 600)`) to `backend/api.py`. Phone normalisation and validation, honeypot and `t_ms < 3000` give the same 201 with `lead_id: null` and no row. Notifications go through `BackgroundTasks`. Verify with tests: the valid "Lan" case stores context and project, "+84 912 345 678" is stored as `0912345678`, "12345" gives a 422 with `so_dien_thoai` in `loc` and no row, the honeypot and fast cases give no row and no notify call, and the 6th call in 10 minutes gives a 429 with Retry-After.
- [x] 3.2 Route `/chat` leads through `create_lead(nguon="chat", ...)`. `Chat` accepts optional `phien_id` and `gui_ho_so`, and `/chat` schedules `notify_new_lead` when a lead was created. Verify that `tests/test_assistant.py` still passes, and that a new test shows a handoff with a consented session stores `nguon='chat'`, the intent, the conversation and a profile.
- [x] 3.3 Have `GET /leads` return the new fields and accept a `nguon` filter. Verify with tests: a form lead and a chat lead are both listed newest first, `?nguon=form` returns only the form lead, and an anonymous call gets 401.

## 4. Contact form (frontend)

- [x] 4.1 Add `createLead(body)` to `src/api.js` and export `visitId` (the existing session-id helper). Let `sendChat` pass `phien_id` and `gui_ho_so`. Verify that `npm run build` passes.
- [x] 4.2 Create `src/components/ContactForm.vue` (props `project`, `spaceId`, `title`) with labelled inputs (name, phone `type=tel`, email, message), the opt-in box shown only when `consent.get()==='yes'`, the personal-data notice, a hidden honeypot, `t_ms`, client-side validation with errors under the fields (`role=alert`, `aria-describedby`), server 422 `loc` mapped to fields, a 429 or network message that keeps the input, the button disabled while sending, and a `role=status` confirmation naming the phone. Verify in the browser at http://localhost:8080/prj1/ by walking each `leads/contact-form` scenario at 1280px and 360px with no horizontal scroll.
- [x] 4.3 Add the "Tư vấn về dự án này" section with `<ContactForm :project="project.slug">` to `src/views/ProjectView.vue`, between the gallery and `pv-nav`. Verify in the browser that a submission from `/du-an/<slug>` shows on `/khach-hang` with that project link, and that the Desktop, Phone and No-description scenarios of `project-detail-page` still hold.
- [x] 4.4 Add the same opt-in box under the contact field in `src/components/ChatWidget.vue` (only when consent is `yes`), and send `phien_id` and `gui_ho_so`. Verify in the browser that an unanswerable question with the box ticked creates a chat lead with a profile on `/khach-hang`.

## 5. Leads page

- [x] 5.1 Update `src/views/LeadsView.vue`. It needs a source chip (`Form liên hệ` / `Trợ lý chat`), the name, a `tel:` phone and a `mailto:` email, the message, a context link (`/du-an/<slug>` or `/khong-gian/<id>`), the profile summary with a `<details>` of viewed-space links, the chat block kept for chat leads, a source filter, and an updated intro line (no longer "Tạo từ trợ lý chat"). Verify in the browser as a `sales` user that the form, chat and old chat leads each render correctly, the filter works, and there is no horizontal scroll at 360px.

## 6. Docs and integration

- [x] 6.1 Document the `D3_SMTP_*` and `D3_SALES_EMAIL` env vars, the `schema.sql` re-apply command and `POST /leads` in `TONG-QUAN-DU-AN.md`, and tell the `/lien-he` (0.3) owner how to embed `<ContactForm />`. Mark roadmap items 1.3 and 1.4 as covered and 1.2 as out of scope per `usecase-0`/`usecase-4`. Verify that the documented psql command runs as written.
- [x] 6.2 Run the full backend suite and an end-to-end check. With consent accepted, view 3 spaces, submit from a project page with the box ticked, and see the lead on `/khach-hang` with the profile and the notification log line. Then decline consent in a new browser session, submit, and see no profile. Verify that `pytest -q` is all green and both cases behave as described. Result: the Playwright run (30/30) covers the declined and consented form, the chat handoff with the profile, `/khach-hang` at 1280/360px, and the 429 state. The log line `lead N (form) mới` shows in `docker compose logs backend`. The lead, assistant, events and ratelimit tests are green (39). The full suite has 7 failures that predate this change and come from the environment: OAuth keys set in `.env`, no CUDA, no photo transcripts, `public/img` missing in the container, and no `working_space` drafts.

## Workflow follow-up

- Archive the change after review (`openspec archive lead-intake`).
- Once archived, the brief (UC08) and the estimate (UC10) changes call `create_lead(nguon='brief' | 'estimate', ...)`.
