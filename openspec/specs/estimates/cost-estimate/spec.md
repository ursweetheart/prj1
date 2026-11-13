# estimates/cost-estimate Specification

## Purpose
Gives a visitor a quick, consistent price range for their project from the price table, with a breakdown and the right warnings, and turns a request for the detailed estimate into a lead (UC10; seq-9, act-6).

## Requirements

### Requirement: Estimate inputs
`/uoc-tinh` SHALL ask for the building type (Căn hộ / Chung cư, Nhà phố, Biệt thự, Văn phòng, Thương mại / Showroom), the area in m² (required, 10–5000), the number of bedrooms (0–10, default 2) and the package (Cơ bản, Tiêu chuẩn, Cao cấp, default Tiêu chuẩn). Invalid input SHALL be reported under the field and no estimate shown.

#### Scenario: Area out of range
- **WHEN** a visitor enters area 5 and presses "Ước tính"
- **THEN** "Diện tích từ 10 đến 5000 m²" appears under the area field

### Requirement: Deterministic formula
For each cost item the range SHALL be area × the item's VND/m² range for that building type and package. The furniture item SHALL be multiplied by 1 + 0.08 × (bedrooms − 2) when there are more than 2 bedrooms. The total SHALL be the sum of the items. The same input SHALL always give the same result for the same price table.

#### Scenario: Apartment, 70 m², 3 bedrooms, standard
- **WHEN** the Căn hộ / Tiêu chuẩn ranges are Thiết kế 0.2–0.3, Phần thô 1.2–1.8, Hoàn thiện 2.2–3.5, Nội thất 3.0–5.0 million VND/m² and a visitor asks for 70 m², 3 bedrooms
- **THEN** the items are 14–21, 84–126, 154–245 and 226.8–378 million, and the total is 478.8–770 million VND

### Requirement: Result with breakdown and warnings
The result SHALL show the total range and one line per cost item, in VND rounded for reading (e.g. "478,8 triệu – 770 triệu", "1,2 tỷ"). It SHALL always say "Ước tính tham khảo, chưa phải báo giá". When any price used is a sample, it SHALL also say "Đơn giá mẫu, chưa phải báo giá của D3 Studio".

#### Scenario: Sample prices
- **WHEN** a visitor gets an estimate while the table still holds sample prices
- **THEN** both the "Ước tính tham khảo" and the "Đơn giá mẫu" notices are shown with the result

#### Scenario: All prices set by D3
- **WHEN** every row used was set by staff
- **THEN** only the "Ước tính tham khảo" notice is shown

### Requirement: Suggested projects
Below the result the page SHALL show up to 3 D3 projects of the same building type (Căn hộ → Chung cư, Nhà phố → Nhà phố, Biệt thự → Villa, Văn phòng → Văn phòng, Thương mại → Showroom / Lounge / F&B), linking to their project pages, or nothing when there is none. Matching by budget SHALL NOT be claimed, because projects carry no investment range yet.

#### Scenario: Villa
- **WHEN** a visitor estimates a Biệt thự
- **THEN** up to 3 villa projects are shown under "Dự án cùng loại của D3"

### Requirement: Ask for the detailed estimate
After a result, "Nhận bản chi tiết qua email" SHALL ask for name, phone and email (all required) with the personal-data notice, using the contact form's validation, spam protection and shared rate limit. The confirmation SHALL name the email address.

#### Scenario: Send the details
- **WHEN** a visitor with a result enters "Lan", "0912345678", "lan@example.com" and sends
- **THEN** they see "Đã gửi bản ước tính chi tiết tới lan@example.com"

#### Scenario: Email missing
- **WHEN** the visitor leaves the email empty
- **THEN** "Vui lòng nhập email để nhận bản chi tiết" appears under the email field and nothing is sent

### Requirement: Estimate lead and emails
On a detailed-estimate request the server SHALL recompute the estimate from the inputs (never trusting a total sent by the client), store a lead with source `estimate` carrying the inputs and the result, email the visitor the detailed breakdown with the notices, and notify the consultants.

#### Scenario: Lead stored
- **WHEN** the 70 m² apartment request is sent with a forged total of 1 VND
- **THEN** the stored lead has source `estimate` and the server's 478.8–770 million result

#### Scenario: Visitor email
- **WHEN** the estimate lead is created and mail is configured
- **THEN** the visitor's email lists the total, every item line and the "Ước tính tham khảo" notice, plus the sample-price notice when samples were used

### Requirement: Way in
The footer SHALL link "Ước tính chi phí" to `/uoc-tinh`. When the assistant answers a price question, its answer SHALL end with a link to `/uoc-tinh` in addition to the request for contact details.

#### Scenario: Price question in chat
- **WHEN** a visitor asks the assistant "chung cư 70m2 làm nội thất hết bao nhiêu"
- **THEN** the answer ends with a line pointing to "/uoc-tinh" for a quick estimate
