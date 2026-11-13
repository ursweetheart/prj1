# Design

## Context

- **Lead intake:** `leads.create_lead(nguon, …, request=…, conn=…)` stores leads, and `nguon = 'estimate'` is already allowed by the CHECK. `LeadIn` carries the contact validation, honeypot `website` and `t_ms`. `limit("leads", 5, 600)` is shared by `/leads` and `/briefs`. `notify.notify_new_lead` / `confirm_to_visitor` already branch on `nguon` (brief).
- **Roles:** `APPROVERS = {lead_architect, admin}`. There is no estimating role, and act-6's "Bộ phận dự toán" maps to the approvers.
- **Projects:** static frontend data (`src/data/projects.js`) with `loai` in `chung-cu | nha-pho | villa | phong | lounge | fnb | khach-san | spa | showroom | van-phong` and no investment range. Spaces carry no `muc_dau_tu` or `loai_cong_trinh` tags today.
- **Chat:** price answers already end with a request for contact details (`assistant.respond`).
- **Schema:** `schema.sql` is idempotent and re-applied by hand on existing databases.

## Goals / Non-Goals

**Goals:**
- Same input, same answer: the estimate is arithmetic on a table, not a model call.
- Honest labelling: sample prices are visible as samples everywhere a number appears (page, email, lead).
- Staff change prices without code, per act-6.

**Non-Goals:**
- Budget matching of projects, PDF quotes, quantity take-off, price history.

## Decisions

### 1. One table, 60 rows, seeded in `schema.sql`
```
don_gia  id, loai_nha, hang_muc, goi, gia_min, gia_max (VND per m², bigint), nguon 'mau'|'d3',
         ghi_chu, cap_nhat_boi -> app_user ON DELETE SET NULL, cap_nhat_luc
         UNIQUE (loai_nha, hang_muc, goi), CHECK (0 <= gia_min AND gia_min <= gia_max)
```
The seed inserts the full grid from a base table times a building-type factor, with `ON CONFLICT (loai_nha, hang_muc, goi) DO NOTHING`, so re-applying never touches edited rows.
- Base (Căn hộ, million VND/m²), as min–max for Cơ bản / Tiêu chuẩn / Cao cấp:
  - Thiết kế: 0.15–0.2 / 0.2–0.3 / 0.3–0.45
  - Phần thô & cải tạo: 0.8–1.2 / 1.2–1.8 / 1.8–2.5
  - Hoàn thiện: 1.5–2.2 / 2.2–3.5 / 3.5–5.5
  - Nội thất: 2.0–3.0 / 3.0–5.0 / 5.0–9.0
- Factors: Căn hộ 1.0, Nhà phố 1.1, Biệt thự 1.3, Văn phòng 0.9, Thương mại 1.15.

These numbers are invented for the demo. That is the reason for the `mau` flag and the notices.
- *Alternative:* a JSON config file. Rejected: act-6 wants staff to edit prices on a page, which needs the database.
- *Alternative:* fewer rows, with a factor column per building type. Rejected: staff think in cells ("biệt thự cao cấp nội thất"), so storing each cell keeps the edit page and the data the same shape.

### 2. Formula in one pure function
`pipeline/estimate.py::compute(prices, loai_nha, dien_tich, so_phong_ngu, goi)` takes the 4 rows for the building type and package and returns
`{tong: {min, max}, hang_muc: [{ma, ten, min, max}], mau: bool}`, with VND as integers.
- Each item is area × range. Furniture is × (1 + 0.08 × max(0, rooms − 2)), the rooms factor from seq-9's "số phòng" input.
- `mau` is true if any of the 4 rows is a sample.
- A thin `estimate(conn, inputs)` loads the rows and calls `compute`. `compute` is pure, so the spec's worked example is a unit test with no database.

### 3. API
| Method | Path | Who | Notes |
| :-- | :-- | :-- | :-- |
| POST | `/estimates` | public, `limit("estimates", 30, 60)` | `EstimateIn{loai_nha, dien_tich_m2 10–5000, so_phong_ngu 0–10 = 2, goi = tieu_chuan}` → result; no lead, nothing stored |
| POST | `/estimates/send` | public, shared `limit("leads", 5, 600)` | `EstimateLeadIn(LeadIn)` + `EstimateIn` fields, `email` required; the server recomputes, then `create_lead("estimate", request={"dau_vao": …, "ket_qua": …})`, then both notices; bot traps get the normal 201 shape with `lead_id: null` |
| GET | `/prices` | approvers | all 60 rows, plus who changed each |
| PUT | `/prices/{id}` | approvers | `{gia_min, gia_max, ghi_chu?}`: 422 if min > max or negative; sets `nguon='d3'`, `cap_nhat_boi`, `cap_nhat_luc` |

The email is required on `/estimates/send` because the whole point is emailing the details. `LeadIn.email` stays optional for the contact form, and `EstimateLeadIn` overrides it.

### 4. Display and the visitor email
- **Format:** below 1 billion, "478,8 triệu"; from 1 billion, "1,25 tỷ". One decimal for millions, two for billions, trailing zeros dropped, Vietnamese decimal comma. The same helper exists in JS (page) and Python (email).
- **Visitor email:** `confirm_to_visitor` for `nguon='estimate'` lists the inputs, the total, every item line and the notice(s). Sales get the same lines through `notify_new_lead`.

### 5. Suggested projects, client-side
The estimate page maps `loai_nha` to project `loai` (`can_ho→chung-cu`, `nha_pho→nha-pho`, `biet_thu→villa`, `van_phong→van-phong`, `thuong_mai→showroom|lounge|fnb`) and shows the first 3 from `PROJECTS_LIST` as the usual project cards. No backend call is needed, because projects are frontend data.

### 6. Staff page
`PricesView.vue` at `/quan-tri/don-gia` (`meta.roles: APPROVERS`) has a building-type switch, and a 4 × 3 grid of min and max inputs in **million VND** (converted to VND on save). Each cell has a "Mẫu" chip while the row is `mau`, and a save button per cell that lights up when the cell is dirty. Errors show inline. The header gets a role link "Đơn giá" for approvers.

### 7. Chat
In `assistant.respond`, a price-intent answer gets an extra line, "Ước tính nhanh theo diện tích: /uoc-tinh". The chat renders text only, so it is a plain path that sales and visitors can follow; making it a link in ChatWidget is out of scope.

## Risks / Trade-offs

- [Sample prices could be mistaken for D3's quote] → Notices on the page, in the email and on the lead. The flag clears only when staff save a row.
- [The rooms factor is a guess] → It is a documented constant in `estimate.py`, easy to change; the spec pins it so tests catch silent changes.
- [Mixed `mau` and `d3` rows while staff are part-way through editing] → The sample notice shows while any used row is a sample, which is the safe direction.

## Migration Plan

Append the table and seed to `schema.sql`, apply it with `docker compose exec -T db psql -U d3 -d d3 < backend/schema.sql`, then rebuild backend and web. Rollback is to redeploy the previous code, which ignores the table.
