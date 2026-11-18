## 1. Schema

- [x] 1.1 In `schema.sql`: `bo_suu_tap.loai` CHECK + `chia_se`; `lead.thong_bao_luc`, `da_thong_bao`; table `tin_nhan_sms`.

## 2. Backend

- [x] 2.1 `POST /collections/share` and the shared reader accepting `chia_se` (design 2). Tests: unpublished ids dropped; the snapshot doesn't change when the collection does; rate limit; more than 60 ids gives 422.
- [x] 2.2 Budget-matched projects in the estimate (design 3). Tests: code parsing; overlap; same type first; the fallback label when there is no data; only published projects.
- [x] 2.3 `pipeline/hours.py` and the deferred chat-lead notification with the due-sender in the maintenance loop (design 5). Tests:
  - `next_open` for Saturday night, Sunday, a weekday inside hours and a weekday before 08:00;
  - a chat lead at night gets the sentence and no immediate notification;
  - the due-sender sends once.
- [x] 2.4 `notify.send_sms` with its log, called from `confirm_to_visitor` (design 6). Tests: not configured gives a logged row with the number masked; a mocked provider gives "sent"; a provider error gives "failed" and the form still succeeds.

## 3. Frontend

- [x] 3.1 `SaveHeart.vue` prompt (design 1).
- [x] 3.2 `CollectionView.vue` "Chia sẻ bộ sưu tập" (copy link, status message); `shareCollection` in `src/api.js`.
- [x] 3.3 `EstimateView.vue` shows `du_an_goi_y` with its heading. `QuizView.vue` shows the suggested projects.
- [x] 3.4 `ChatWidget.vue` shows the expected-contact sentence (it is part of the answer text; check that it renders).

## 4. Verification

- [x] 4.1 Browser on Docker:
  - signed-out save shows the prompt once;
  - share a collection and open the link in a fresh context;
  - an estimate shows the fallback projects;
  - the quiz shows projects;
  - a chat lead with the clock set outside hours (env override) shows the time;
  - the SMS log row after the contact form.

  Full `pytest` and `npm test` green.

## Results (2026-11-18)

- **Browser, headless, as a visitor (evening in Vietnam, so outside working hours):**
  - saving a photo signed out showed "Đã lưu vào bộ sưu tập. Đăng ký để không mất bộ sưu tập." once, and not on the second save;
  - "Chia sẻ bộ sưu tập" copied a read-only link with 2 photos, and a fresh browser opened it;
  - the estimate listed 3 projects under "Cùng loại công trình (chưa có dữ liệu ngân sách)" (no project has a budget yet);
  - the quiz result listed 3 suggested projects, linked to their pages at the right photo;
  - a chat appointment request answered "Đội tư vấn sẽ liên hệ…" and the lead was deferred to 08:00 Thursday (UTC+7), not notified;
  - the contact form logged an SMS attempt as `*******678 chua_cau_hinh`.
- **Cleanup:** the test leads, conversation, SMS rows and shared snapshot were removed.
- **Tests:** `pytest` 535 passed (3 known environment failures); `npm test` 88 passed.
- **Test isolation:** a conftest fixture now fixes working hours to all day for every test, because a chat lead is deferred outside hours and the suite must not depend on the clock.
