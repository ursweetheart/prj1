# Spec Delta

## Purpose

Holds the unit prices the cost estimate uses (price table D8 in the diagrams), so the estimating staff can change prices without touching code. Until D3 enters its own prices, the table holds sample prices that are clearly marked as such.

## ADDED Requirements

### Requirement: One price range per building type, item and package
The price table SHALL hold, for each of the 5 building types (`can_ho`, `nha_pho`, `biet_thu`, `van_phong`, `thuong_mai`), each of the 4 cost items (`thiet_ke`, `phan_tho`, `hoan_thien`, `noi_that`) and each of the 3 packages (`co_ban`, `tieu_chuan`, `cao_cap`), exactly one range of VND per m² (minimum ≤ maximum, both ≥ 0), its source (`mau` or `d3`), and when and by whom it was last changed.

#### Scenario: Complete table
- **WHEN** the database is created from `schema.sql`
- **THEN** the table has 60 rows, one for every combination, each with minimum ≤ maximum

### Requirement: Sample prices until D3 sets its own
A fresh database SHALL be seeded with sample prices, each flagged `mau`. Re-applying `schema.sql` SHALL NOT overwrite a price staff have changed.

#### Scenario: Re-apply keeps staff prices
- **WHEN** staff set the Căn hộ / Hoàn thiện / Tiêu chuẩn range to 2.5–3.8 million VND/m² and `schema.sql` is applied again
- **THEN** that row is still 2.5–3.8 million and flagged `d3`

### Requirement: Staff edit the prices
`/quan-tri/don-gia` SHALL be a page for the lead architect and admin showing the table per building type (items as rows, packages as columns, a min–max range per cell) with a visible "Mẫu" mark on sample rows. Saving a cell SHALL store the range, flag it `d3`, and record who and when. Estimates SHALL use the new value at once. Other roles SHALL get 403 from the API and SHALL NOT see the page or its menu link.

#### Scenario: Edit one cell
- **WHEN** a lead architect changes Biệt thự / Nội thất / Cao cấp to 8–14 million and saves
- **THEN** the cell shows 8–14 million without the "Mẫu" mark, and the next estimate for that combination uses it

#### Scenario: Invalid range
- **WHEN** a lead architect enters a minimum above the maximum
- **THEN** the page shows "Giá thấp nhất phải nhỏ hơn hoặc bằng giá cao nhất" and nothing is saved

#### Scenario: Sales user
- **WHEN** a sales user calls `PUT /prices/{id}`
- **THEN** the response is 403
