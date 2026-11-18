# Proposal

## Why

Once a photo is published, nothing can take it down. The review page can only return photos that are still on their way to publication. The `photo-review` spec even says "A published photo … SHALL NOT be returned". `TONG-QUAN-DU-AN.md` lists "Chưa gỡ được ảnh đã đăng" against UC14.

Real reasons to take a photo down come up after publishing:
- a mistake found later (wrong style label, a client's face or address visible);
- a client who withdraws their consent to publication.

The second is a legal matter. The photos come from Behance and were cleared only for the demo, and the doc already warns that real use needs the client's permission.

## What Changes

- **"Gỡ khỏi website" (take down)** on the review page's "Đã đăng" tab, for the lead architect and admin, for one photo or a selection, always with a reason (5–500 characters). There are two outcomes:
  - **"Gỡ xuống để sửa"** → the photo goes back to "Nháp". To be published again it goes through the whole flow, including the rights confirmation.
  - **"Gỡ và lưu nội bộ"** → the photo becomes "Lưu nội bộ" (the client withdrew consent). It is never shown publicly and can only be reopened with a reason, as today.
- **The same guarantees as the other backward paths:**
  - all or nothing for a selection;
  - the reason shown on the photo's card ("Đã gỡ khỏi website: …") until it moves on;
  - every take-down in the review log with user, time, before and after;
  - the uploader is told, by email or in the log.
- **Gone from every public place at once:** the space page, the portfolio and search, the project's spaces, the style quiz, chat answers, item listings, project results and saved collections.
  - Visitors' saved lists and sent briefs already show only published photos, so the photo drops out of them. It comes back if the photo is published again.
  - A test covers each public endpoint.
- **Returning a published photo with "Trả về nháp" keeps answering 409,** as specified. Taking a published photo down is its own action, with its own wording, so it can't happen by accident from a mixed selection.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `photo-review`: added requirements for taking a published photo down (to draft, or to internal), who may do it, its reason, log and notice, and that it leaves no public trace. The existing requirements are unchanged; "Trả về nháp" still refuses published photos.

## Impact

- **Backend:**
  - `backend/api.py`: `POST /spaces/unpublish {space_ids, ly_do, giu_noi_bo}`, a new `BACK` entry for each target, and reason kinds `go_xuong` / `go_noi_bo`;
  - `backend/pipeline/notify.py`: the notice wording for the two kinds;
  - new `backend/tests/test_unpublish.py`.
- **Frontend:**
  - `src/api.js` (`unpublishSpaces`);
  - `src/views/ReviewView.vue` (ours): on the "Đã đăng" tab, a per-photo "Gỡ khỏi website" and a bulk button, both through the existing reason dialog, which gets a choice of outcome; the card shows the take-down reason.
- **No schema change.** It uses `review_status`, `ly_do_duyet` and `review_log`.
- **Known limit, not fixed here:** image files are served at `/images/<path>` whatever the photo's status (drafts included, already today). Someone who saved a direct image URL can still open it. Closing that needs signed or staff-only image URLs, which goes on the fixing list. It is noted in the doc.
- **Out of scope:**
  - scheduled take-downs;
  - an expiry date on publication rights;
  - telling visitors who saved the photo.
