# Proposal

## Why

Several visitor-facing steps in the diagrams are missing or cut short:
- **seq-13 step 3:** the "đã lưu, mời đăng ký" prompt after saving while signed out.
- **BFD 2.3:** sharing a saved collection.
- **seq-9 steps 6-7, act-6:** projects in the same budget range as an estimate.
- **seq-12 steps 12-15:** suggested projects on the quiz result.
- **act-4 "Trong giờ làm việc?":** outside working hours the chat should tell the visitor when they will be called, and notify the team at the start of the next working period.
- **seq-5 step 11, seq-7 step 9, act-8:** SMS confirmations.

## What Changes

- **Save prompt:** after a signed-out visitor saves a photo with the heart, a short note invites them to sign up so the collection isn't lost (once per browser session), with a link.
- **Share a saved collection:** "Chia sẻ bộ sưu tập" on `/bo-suu-tap` creates a read-only link to a snapshot of the current collection (signed in or not), using the existing shared-collection page.
- **Budget-matched projects in the estimate:**
  - the result lists up to 3 published projects whose investment level overlaps the estimated range;
  - when no project has budget data, it lists projects of the same type, labelled "Cùng loại công trình (chưa có dữ liệu ngân sách)".
- **Quiz result:** the result page shows the up to 3 suggested projects the API already returns.
- **Working hours for chat hand-offs:**
  - working hours are configurable (default Monday-Saturday 08:00-17:30, UTC+7);
  - outside them, a chat lead's answer tells the visitor when to expect contact, and the team notification is sent when the next working period starts.
- **SMS channel:**
  - visitor confirmations also go by SMS when the visitor gave a phone number and an SMS provider is configured;
  - without a provider, the message is recorded as not sent, the same way email works today.

## Capabilities

### New Capabilities
- `visitor-touchpoints`: the save prompt, sharing a saved collection, budget-matched projects on the estimate, quiz project suggestions, working-hours hand-off and SMS confirmations.

### Modified Capabilities
(none: each item adds behaviour without changing an existing requirement)

## Impact

- **Backend:**
  - `api.py`: `POST /collections/share`, the estimate response, chat lead timing;
  - `pipeline/estimate.py`;
  - `pipeline/notify.py`: deferred notifications, SMS;
  - `pipeline/leads.py`;
  - `schema.sql`: `bo_suu_tap.loai` + `chia_se`, `lead.thong_bao_luc` / `da_thong_bao`, `tin_nhan_sms` log;
  - the maintenance loop sends due notifications.
- **Frontend:** `SaveHeart.vue`, `CollectionView.vue`, `EstimateView.vue`, `QuizView.vue`, `ChatWidget.vue` (shows the expected contact time), `src/api.js`.
