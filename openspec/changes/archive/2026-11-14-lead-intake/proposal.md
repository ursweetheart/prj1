# Proposal

## Why

The diagrams have every lead source go through one intake step: the contact form, the collection-as-brief, the chat handoff and the cost estimate (dfd-2-4 4.1/4.2, act-2, seq-5, seq-7, seq-9). That step creates the lead, attaches the visitor's behaviour profile and notifies the consultants. Today only the chat creates leads. It stores them as a bare `contact` string, attaches no behaviour, and tells nobody: sales has to open `/khach-hang` to find out. The website has no way to say "call me about this project" either. Every later sales feature (brief, estimate, `/lien-he`) needs this step first.

Per `usecase-0` and `usecase-4`, contacting, assigning and following up a lead happen **outside the system**. This change therefore stops at "lead stored + consultants notified" and does not add a lead lifecycle.

## What Changes

- New public endpoint `POST /leads` (UC11, seq-5). It takes name, phone, optional email and an optional message, plus the context the visitor was in: the page and the project slug or space id. It validates the phone format and keeps the entered data on error. It guards against spam with a rate limit, a hidden honeypot field and a minimum fill time. The lead is stored with `nguon = 'form'`.
- One shared intake function creates every lead and notifies the consultants. The chat handoff (`/chat`) moves onto it, so chat leads get the same fields, the same profile and the same notification. Later sources (brief, estimate) only add a `nguon` value.
- Behaviour profile on the lead (act-2 "Gắn hồ sơ hành vi"). The intake attaches a snapshot from the visitor's consented session: the spaces viewed and the facet values seen most. The visitor must also tick "send what I viewed" on the form. Without consent, nothing is attached.
- Consultant notification (seq-5 #12, dfd-2-4 4.2). The intake emails the sales inbox with the contact, the context and the profile summary when SMTP is configured. The visitor gets an email confirmation when they gave an email. Without SMTP, the notification is logged and the lead still shows as new on `/khach-hang`. SMS is not included.
- A reusable `ContactForm` component (≤ 5 visible fields, with a personal-data notice). The project page gets a "Tư vấn về dự án này" block under the gallery with the form, and the teammate's `/lien-he` page (roadmap 0.3) can embed the same component.
- `/khach-hang` shows every source: a source chip, the name, phone and email, the message, the project or page the lead came from, and the behaviour profile. It keeps the chat transcript for chat leads.
- **BREAKING (internal):** the `lead` table gains `nguon`, `ho_ten`, `so_dien_thoai`, `email`, `loi_nhan`, `ngu_canh`, `ho_so_hanh_vi` and `phien_id` columns. `intent` becomes nullable. Existing chat rows are backfilled as `nguon = 'chat'`. The `GET /leads` response gains these fields.

## Capabilities

### New Capabilities
- `leads/lead-intake`: how a lead enters the system from any source. Covers validation, spam protection, the consented behaviour profile, the consultant and visitor notifications, and how staff see the lead.
- `leads/contact-form`: the visitor-facing contact form. Covers its fields, the personal-data notice, inline errors, the success state, and placement on the project page and in `/lien-he`.

### Modified Capabilities
- `project-detail-page`: the "Project page" requirement adds a contact block between the gallery and the previous/next links.

## Impact

- **Backend:** `backend/schema.sql` (lead columns and backfill), `backend/api.py` (`POST /leads`, the `GET /leads` fields, `/chat` passes `phien_id`), `backend/pipeline/assistant.py` (`_create_lead` → shared intake), new `backend/pipeline/leads.py` (intake, profile, notify), and new `backend/tests/test_leads.py`.
- **Config:** optional `D3_SMTP_HOST/PORT/USER/PASSWORD/FROM` and `D3_SALES_EMAIL` env vars. Nothing new is needed to run the demo.
- **Frontend:** `src/api.js` (`createLead`, a `phien_id` in chat), new `src/components/ContactForm.vue`, `src/views/ProjectView.vue`, `src/views/LeadsView.vue`, and `src/components/ChatWidget.vue` (sends the session id).
- **Coordination:** the teammate building `/lien-he` (0.3) embeds `ContactForm` instead of building a separate form.
- **Out of scope:** lead statuses and assignment (handled outside the system per the use-case notes), SMS, collections and brief (UC07/UC08), the cost estimate (UC10), and the full consent preferences (act-7 "Tùy chỉnh", delete requests).
