# search-explanations Specification

## Purpose
TBD - created by archiving change search-explanations. Update Purpose after archive.

## Requirements

### Requirement: Reasons on similar spaces
Each similar space SHALL carry a reason listing the labels it shares with the source space by display name: room type, style and up to 2 more visible dimensions, at most 3 in all, never `khac` (seq-2 steps 9-10). The card SHALL show it under the photo. A result sharing no label SHALL show no reason line.

#### Scenario: Shared style and tone
- **WHEN** space 12 is a Japandi living room in warm tones and similar space 30 is a Japandi bedroom in warm tones
- **THEN** space 30 shows "Cùng phong cách Japandi · Cùng tông màu Ấm"

### Requirement: Interior check on uploaded photos
Before searching, an uploaded photo SHALL be checked for being an interior (seq-8 steps 4-6). A photo judged not to be an interior SHALL get no results and the message "Ảnh này có vẻ không phải ảnh nội thất. Bạn thử một ảnh chụp căn phòng khác nhé." The photo SHALL still never be stored.

#### Scenario: Logo uploaded
- **WHEN** a visitor uploads a company logo
- **THEN** no results are shown, only that message

#### Scenario: Room photo
- **WHEN** a visitor uploads a photo of a living room
- **THEN** results are shown

### Requirement: Traits of an uploaded photo
For an interior photo, the answer SHALL include its likely style and tone, each with a confidence, judged from the closest library photos (seq-8 step 13). The page SHALL show "Ảnh của bạn có vẻ thuộc phong cách X, tông màu Y" above the results. A trait whose confidence is under 40% SHALL be left out of the sentence.

#### Scenario: Wabi-sabi photo
- **WHEN** most of the closest library photos are Wabi-sabi in warm tones
- **THEN** the page says "Ảnh của bạn có vẻ thuộc phong cách Wabi-sabi, tông màu Ấm"

### Requirement: Constraints taken from a description
Room-type and style words in a description, matched by name, code or synonym with accents and case ignored, SHALL become hard filters, and only the remaining words SHALL be compared by meaning (seq-11 steps 3-7). The answer SHALL list the constraints it took, and the page SHALL show them as "Đã lọc: Phòng khách · Japandi".

#### Scenario: Room type in the sentence
- **WHEN** a visitor searches "phòng khách ấm cúng gỗ sáng nhiều cây xanh"
- **THEN** only living rooms are returned, and "Đã lọc: Phòng khách" is shown

### Requirement: Reasons on description results
Each description result SHALL carry the labels of the result that match the description's words or constraints by display name (seq-11 step 11), shown like the similar-space reasons.

#### Scenario: Matching material
- **WHEN** the description mentions "gỗ" and a result carries the material value "Gỗ tự nhiên"
- **THEN** that result's reason includes "Gỗ tự nhiên"

### Requirement: Rewording hint on weak matches
When the best description match scores below the weak-match threshold, the answer SHALL carry a hint and the page SHALL show "Ít kết quả thật sát. Bạn thử mô tả cụ thể hơn: loại phòng, phong cách, vật liệu hoặc màu sắc." (seq-11 step 12). Results that exist SHALL still be listed.

#### Scenario: Vague description
- **WHEN** a visitor searches "đẹp"
- **THEN** the hint is shown with the results
