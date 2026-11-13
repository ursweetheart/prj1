# Tasks

Backend tests: `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`. Frontend: `docker compose build web`; vitest runs in a throwaway `node:22-alpine` container on a copy of the sources. Browser checks use the scratchpad Playwright pattern at 1280px and 360px.

## 1. Price table

- [x] 1.1 Append the `don_gia` table and the sample seed (base × building-type factor, `nguon='mau'`, `ON CONFLICT DO NOTHING`) to `backend/schema.sql`. Verify that applying it twice gives no error, that there are 60 rows with min ≤ max, that Căn hộ / Tiêu chuẩn reads 0.2–0.3, 1.2–1.8, 2.2–3.5 and 3.0–5.0 million, and that a row edited to `d3` survives a re-apply (test in `tests/test_estimates.py`).

## 2. Estimate backend

- [x] 2.1 Create `backend/pipeline/estimate.py` with the pure `compute()` (items, rooms factor, total, `mau`), the DB `estimate()`, and the VND formatter. Verify with tests: the spec's 70 m², 3-bedroom example gives 478.8–770 million exactly; 2 bedrooms gives no furniture uplift; `mau` follows the rows; the formatter gives "478,8 triệu", "770 triệu", "1,25 tỷ".
- [x] 2.2 Add `POST /estimates` and `POST /estimates/send` to `backend/api.py`. Verify with tests: valid input returns the breakdown; area 5 and an unknown type give 422; send stores `nguon='estimate'` with `dau_vao` and a server-computed `ket_qua` (a client-sent total is ignored); a missing email gives 422; the honeypot gives 201 with a null id and no row; the 6th lead/brief/estimate in 10 minutes gives 429.
- [x] 2.3 Add `GET /prices` and `PUT /prices/{id}` (approvers). Verify with tests: a lead architect edit stores the range, `d3`, who and when, and the next estimate uses it; min > max or a negative value gives 422; sales and anonymous callers get 403/401.
- [x] 2.4 Add the estimate lines to `notify.py` (inputs, total, items, notices) for both emails, and have `GET /leads` keep `request` for estimate leads with `nguon=estimate` filtering. Verify with FakeSMTP tests: the visitor email lists every item and both notices while samples are used; the sales email names "Ước tính chi phí"; `?nguon=estimate` returns only estimates.
- [x] 2.5 Add the `/uoc-tinh` line to price-intent answers in `assistant.respond`. Verify that a test asking "chung cư 70m2 làm nội thất hết bao nhiêu" gets an answer containing "/uoc-tinh", and that `tests/test_assistant.py` still passes.

## 3. Frontend

- [x] 3.1 Add `estimate`, `sendEstimate`, `getPrices` and `savePrice` to `src/api.js`, and a `formatVnd` helper in `src/lib/money.js` with `money.test.js` (the same cases as the Python formatter). Verify that vitest passes.
- [x] 3.2 Create `EstimateView.vue` at `/uoc-tinh`: inputs with inline errors, the result with total, item lines and notices, up to 3 same-type projects, and the "Nhận bản chi tiết qua email" form (name, phone, email, notice, honeypot, `t_ms`, 422/429 handling, confirmation naming the email). Add the footer link. Verify in the browser: the spec's example shows "478,8 triệu – 770 triệu" with both notices; area 5 shows the error; a villa shows villa projects; sending creates the lead and the confirmation; no horizontal scroll at 360px.
- [x] 3.3 Create `PricesView.vue` at `/quan-tri/don-gia` and the "Đơn giá" role link for approvers. Verify in the browser as the lead architect: switch type, edit one cell, see "Mẫu" disappear, and a new estimate uses the value; min > max shows the inline error; a sales user sees no link and is redirected from the page.
- [x] 3.4 Add the estimate block (inputs line, total, "đơn giá mẫu" mark) and the "Ước tính" filter chip to `LeadsView.vue`. Verify in the browser as a sales user that the block and filter work, with no horizontal scroll at 360px.

## 4. Docs and integration

- [x] 4.1 Update `TONG-QUAN-DU-AN.md`: UC10, roadmap 2.4, the API table, the `don_gia` table, and a note that sample prices must be replaced at `/quan-tri/don-gia` before real use. Verify that the documented endpoints exist in `/openapi.json`.
- [x] 4.2 Run the integration check: full backend suite (only known failures), vitest, the lead-intake and collection Playwright scripts, and the new estimate checks. Restore any price edited during the checks to its sample value. Verify and record the results here. Result: backend 143 passed and 8 failed, the same 8 known failures (7 environment ones plus `test_project_spaces` on the mixed-case `Indochine` folder); vitest 33/33; browser scripts lead-intake 30/30, collection 31/31, estimate 19/19. The price table is back to 60 sample rows. Fixed along the way: at 360px the price page scrolled sideways, because the visually-hidden labels escaped the table's scroll box (`.pr-scroll` is now `position: relative`).
