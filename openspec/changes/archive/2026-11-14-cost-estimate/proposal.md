# Proposal

## Why

"Bao nhiêu tiền?" is the question visitors ask most, and today only the chat handles it, from a few knowledge-base entries. The diagrams give the estimate its own flow (UC10, BFD 2.6; seq-9, act-6, dfd-2-2 with price table D8): the visitor enters the house type, area, rooms and a material package, gets a price range with a breakdown, and can ask for the details by email, which becomes a lead. It is the last lead source the intake is missing (`nguon = 'estimate'` is already allowed).

D3 has no price list. The estimator therefore runs on **sample prices clearly marked "tham khảo"**. act-6 says the estimating team updates prices in an admin screen without changing code, so staff get a page to replace them; edited rows stop being marked as samples.

## What Changes

- A price table (D8) with one row per building type × cost item × package: 5 building types (Căn hộ / Chung cư, Nhà phố, Biệt thự, Văn phòng, Thương mại / Showroom) × 4 items (Thiết kế, Phần thô & cải tạo, Hoàn thiện, Nội thất) × 3 packages (Cơ bản, Tiêu chuẩn, Cao cấp). Each row has a VND/m² range, a source flag (`mau` = sample, `d3` = set by staff), and who changed it and when.
- The table is seeded with sample prices, flagged `mau`.
- A public estimate page `/uoc-tinh`: house type, area, bedrooms, package → total range, breakdown per item, and up to 3 D3 projects of the same building type. The page always says "Ước tính tham khảo"; while any price used is a sample, it also says "Đơn giá mẫu, chưa phải báo giá của D3 Studio". The calculation is a fixed formula on the table, so the same input always gives the same result.
- "Nhận bản chi tiết qua email": name, phone and email (required here) → a lead with source `estimate` carrying the inputs and the result. The visitor gets the detailed breakdown by email, and sales get the usual notice.
- A staff page `/quan-tri/don-gia` (lead architect, admin) to edit the ranges. A saved row becomes `d3`, and estimates use it immediately.
- `/khach-hang` shows estimate leads with their inputs and result.
- Links to `/uoc-tinh` from the footer and from the chat answer to a price question.

## Capabilities

### New Capabilities
- `estimates/cost-estimate`: the estimate page, its inputs, the formula, the result, the sample-price notice, suggested projects, and the "send me the details" lead.
- `estimates/price-table`: the price table, its sample seed, and the staff page that edits it.

### Modified Capabilities
- `leads/lead-intake`: "Sales staff see every lead" also covers estimate leads (inputs and result) and the `estimate` filter.

## Impact

- **Backend:** `backend/schema.sql` (table `don_gia` + sample seed), new `backend/pipeline/estimate.py` (formula), `backend/api.py` (`POST /estimates`, `POST /estimates/send`, `GET /prices`, `PUT /prices/{id}`), `backend/pipeline/notify.py` (estimate lines; the detailed breakdown in the visitor email), `backend/pipeline/assistant.py` (link in price answers), and new `backend/tests/test_estimates.py`.
- **Frontend:** new `src/views/EstimateView.vue` (`/uoc-tinh`), new `src/views/PricesView.vue` (`/quan-tri/don-gia`), `src/api.js`, `src/router/index.js`, `src/components/SiteNav.vue` (staff link "Đơn giá"), `src/components/SiteFoot.vue` (link), `src/views/LeadsView.vue`.
- **Out of scope:** real D3 prices (staff enter them later), matching projects by budget (projects carry no investment range yet), AI-researched market prices, PDF quotes, per-room or per-item quantity take-off.
