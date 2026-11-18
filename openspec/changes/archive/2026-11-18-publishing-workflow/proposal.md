# Proposal

## Why

seq-6 and act-1 (QT-01) draw a publishing workflow the code shortens:
- **The editing step.** After labelling, the photo waits in "Chờ biên tập" for the content staff, who edit the text and SEO and then send it on for professional review. Both hand-overs notify the next person. Today an architect sends a draft straight to "Chờ duyệt" and nobody is notified.
- **Required dimensions.** act-1 checks "Đủ các features bắt buộc?" before a draft can leave, which the code does not.
- **Publish date.** seq-6 step 17 records the publish date.
- **Image sizes.** act-1 starts by optimising the photo and making several sizes (class-6 Anh `cac_kich_thuoc`, `chieu_rong`, `chieu_cao`), but every page loads the original file.
- **Assistant knowledge.** seq-6 step 18 loads a published photo into the assistant's knowledge, but the photo descriptions the assistant searches are only written by an offline script (0 rows today).

## What Changes

- **New status `editing` ("Chờ biên tập")** between draft and in review: draft → editing → in_review → approved → cleared → published.
  - Staff send a draft to editing, which needs every required dimension filled.
  - The content staff (or an approver) edit the text and send it to review.
  - "Trả về nháp" also works from editing.
- **Notifications:**
  - sending to editing emails the content staff;
  - sending to review emails the lead architects;
  - one email per action, listing the photos.
- **Publish date:** stored on each photo when it is published, and shown in the API and on the review card.
- **Image sizes:** each photo gets WebP copies at 480, 960 and 1600 px wide plus its pixel size, when processed and by a backfill. Pages we own use them through `srcset`.
- **Publishing loads the assistant's knowledge:** a description of the photo, built from its caption, labels, materials, palette and items, is written and embedded through the task queue (no Gemini call).
- **BREAKING:** `POST /spaces/{id}` with `advance` from draft now goes to `editing`, not `in_review`.

## Capabilities

### New Capabilities
- `publishing-workflow`: the editing stage, the required-dimension check, hand-over notifications, the publish date and loading published photos into the assistant's knowledge.
- `image-sizes`: optimised copies at several widths and the photo's pixel size.

### Modified Capabilities
- `photo-review`: "Who may return" and "Return to draft with a reason" also cover the editing status.

## Impact

- **Backend:**
  - `api.py`: `NEXT`, `_advance`, `RETURNABLE`, notifications, the review list fields;
  - `pipeline/notify.py`;
  - new `pipeline/image_sizes.py`, called from `processor` / intake;
  - `pipeline/intake.py`: a new task kind `nap_tri_thuc`;
  - `schema.sql`: `ngay_xuat_ban`, `kich_thuoc`, `chieu_rong`, `chieu_cao`, `space_text.mo_hinh`;
  - a backfill command.
- **Frontend:**
  - `src/api.js` (`NEXT_STATUS`, `STATUS_VI`, `RETURNABLE`, `imageSrcset`);
  - `ReviewView.vue` (status tab, `canEditText`, required-dimension message, publish date);
  - `SpaceTile.vue` (`srcset`).
- **Depends on** `labelling-queue-feedback` (task queue).
