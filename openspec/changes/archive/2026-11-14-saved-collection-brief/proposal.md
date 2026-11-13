# Proposal

## Why

The visitor can now find spaces they like (`/khong-gian`, the space pages), but cannot keep them or tell D3 Studio "this is what I want". In the diagrams this is the main bridge from browsing to a qualified lead: save photos with a heart, add notes, and send the set to an architect as a design brief (UC07, UC08; seq-13, act-8, seq-7, BFD 2.1–2.2). Lead intake (`leads/lead-intake`) already stores leads and notifies sales, so the brief is the next missing piece, and it does not overlap with the pages the teammates are building.

## What Changes

- A heart on every space tile on `/khong-gian` and on the space page saves the photo to "Bộ sưu tập". A header link shows the count.
- Saving works without an account. The collection is kept in the browser (act-8 "lưu trong trình duyệt"), and the collection page invites the visitor to sign up so it isn't lost.
- With an account, the collection is stored on the server. When a visitor signs up or signs in, the browser collection is merged into the account and then cleared (seq-13).
- A collection page `/bo-suu-tap` lists the saved photos with a short note per photo, a remove action and "Gửi cho kiến trúc sư".
- The design brief (seq-7, act-8) is a form with name, phone, optional email, house type, area, budget and a note. Anyone can send it, signed in or not. It is sent through the existing intake as a lead with source `brief`. The saved photos and notes are attached, with a summary of what they have in common (leading style with its share, recurring colour tone, room types, e.g. "Wabi-sabi 60% · tông gỗ sáng · phòng khách").
- Each sent brief gets a read-only share link `/bo-suu-tap/xem/<ma>`. It goes into the email to sales, into the visitor's confirmation email, and into `/khach-hang`.
- `/khach-hang` shows brief leads with the house type, area, budget, the summary, and the photos with their notes.

## Capabilities

### New Capabilities
- `collections/saved-collection`: saving photos with a heart, notes per photo, browser vs account storage, merging at sign-in, the collection page, and the read-only shared view.
- `leads/design-brief`: sending a collection to an architect. Covers the form, validation, the lead it creates, the summary of the photos, the share link and the notices.

### Modified Capabilities
- `leads/lead-intake`: the "Sales staff see every lead" requirement now also covers brief leads (house type, area, budget, summary, photos with notes, share link) and the `brief` filter.

## Impact

- **Backend:** `backend/schema.sql` (tables `bo_suu_tap` and `bo_suu_tap_anh`, lead column `bo_suu_tap_id`), `backend/api.py` (collection endpoints, `POST /briefs`, `GET /leads` fields), `backend/pipeline/leads.py` (brief summary), `backend/pipeline/notify.py` (brief lines and share link in both emails), and a new `backend/tests/test_collections.py`.
- **Frontend:** `src/api.js` (collection store: browser or account, merged at sign-in), a new `src/components/SaveHeart.vue`, a new `src/views/CollectionView.vue` (`/bo-suu-tap`, `/bo-suu-tap/xem/:ma`), a new `src/components/BriefForm.vue`, `src/components/SpaceTile.vue`, `src/views/SpaceView.vue`, `src/components/SiteNav.vue` (count link), `src/router/index.js` and `src/views/LeadsView.vue`.
- **Teammates:** the heart sits on Tùng's space tile and space page. It is an added control and doesn't change their layout or the existing spec requirements.
- **Out of scope:** an editable public share link (the shared view is read-only and only for sent briefs), several named collections per user, hearts in the project photo viewer (few project photos are linked to spaces yet), a "saved a photo" behaviour event for trend analysis (phase 3), and SMS.
