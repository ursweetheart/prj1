## 1. Schema

- [ ] 1.1 In `schema.sql`: `bo_suu_tap.loai` CHECK + `chia_se`; `lead.thong_bao_luc`, `da_thong_bao`; table `tin_nhan_sms`.

## 2. Backend

- [ ] 2.1 `POST /collections/share` and the shared reader accepting `chia_se` (design 2). Tests: unpublished ids dropped; the snapshot doesn't change when the collection does; rate limit; more than 60 ids gives 422.
- [ ] 2.2 Budget-matched projects in the estimate (design 3). Tests: code parsing; overlap; same type first; the fallback label when there is no data; only published projects.
- [ ] 2.3 `pipeline/hours.py` and the deferred chat-lead notification with the due-sender in the maintenance loop (design 5). Tests:
  - `next_open` for Saturday night, Sunday, a weekday inside hours and a weekday before 08:00;
  - a chat lead at night gets the sentence and no immediate notification;
  - the due-sender sends once.
- [ ] 2.4 `notify.send_sms` with its log, called from `confirm_to_visitor` (design 6). Tests: not configured gives a logged row with the number masked; a mocked provider gives "sent"; a provider error gives "failed" and the form still succeeds.

## 3. Frontend

- [ ] 3.1 `SaveHeart.vue` prompt (design 1).
- [ ] 3.2 `CollectionView.vue` "Chia sẻ bộ sưu tập" (copy link, status message); `shareCollection` in `src/api.js`.
- [ ] 3.3 `EstimateView.vue` shows `du_an_goi_y` with its heading. `QuizView.vue` shows the suggested projects.
- [ ] 3.4 `ChatWidget.vue` shows the expected-contact sentence (it is part of the answer text; check that it renders).

## 4. Verification

- [ ] 4.1 Browser on Docker:
  - signed-out save shows the prompt once;
  - share a collection and open the link in a fresh context;
  - an estimate shows the fallback projects;
  - the quiz shows projects;
  - a chat lead with the clock set outside hours (env override) shows the time;
  - the SMS log row after the contact form.

  Full `pytest` and `npm test` green.
