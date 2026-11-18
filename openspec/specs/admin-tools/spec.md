# admin-tools Specification

## Purpose
TBD - created by archiving change admin-tools. Update Purpose after archive.

## Requirements

### Requirement: On-demand object suggestions in the hotspot editor
The hotspot editor SHALL offer "AI gợi ý vật thể" to staff (seq-14 steps 6-9). It SHALL run the local furniture detector on the photo and return each detected object:
- its Vietnamese name;
- its box and centre in 0..1 coordinates;
- its confidence.

No external AI service SHALL be called. Each suggestion SHALL be shown as a distinct dashed marker. Accepting it SHALL add a hotspot at its centre with source "AI" and its confidence, and nothing SHALL be stored until the editor is saved. Suggestions overlapping an existing hotspot of the same name SHALL be left out. Other roles SHALL get 403.

#### Scenario: Suggest and accept
- **WHEN** an architect clicks "AI gợi ý vật thể" on a living-room photo and accepts the suggested "Ghế sofa"
- **THEN** a hotspot "Ghế sofa" with source "AI" appears, and after saving it is stored with its confidence

#### Scenario: Already marked
- **WHEN** the photo already has a hotspot "Ghế sofa" inside the detected sofa's box
- **THEN** no sofa suggestion is shown

### Requirement: Item price range
An item SHALL have an optional price range text of at most 60 characters (class-6 MonDo `khoang_gia`), editable wherever an item's other details are edited, and shown to staff. It SHALL NOT be shown to visitors.

#### Scenario: Set a range
- **WHEN** a staff member sets "12 – 18 triệu" on the item "Ghế sofa da"
- **THEN** the item list shows it, and the visitor's hotspot card does not

### Requirement: Merge queues an index refresh
After two taxonomy values are merged, the system SHALL queue a task that refreshes the search-index entries of every photo that carried the source value: their photo descriptions and the descriptions' embeddings (seq-15 steps 20-22). The merge answer SHALL report "Đã gộp; chỉ mục đang được cập nhật cho N ảnh". Afterwards, no photo description SHALL name the merged-away value.

#### Scenario: Merge Wabi-sabi into Japandi
- **WHEN** an approver merges "Wabi-sabi" into "Japandi" and 6 published photos carried Wabi-sabi
- **THEN** the answer reports 6 photos queued, and after the task runs their descriptions say Japandi

### Requirement: Account full name
Accounts SHALL have an optional full name of at most 100 characters (class-6 NguoiDung `ho_ten`). It can be set:
- at sign-up;
- in an invitation;
- by an admin;
- by the user for their own account.

It SHALL be shown in the account list and in staff emails where the account is named.

#### Scenario: Admin sets a name
- **WHEN** the admin sets "Nguyễn Văn An" on an architect's account
- **THEN** the account list shows it, and that architect sees it on their account

### Requirement: Embedding model recorded
Every stored photo embedding and photo-description embedding SHALL record the name of the model that made it (class-6 VectorAnh / VectorMoTa `ten_mo_hinh`).

#### Scenario: New photo
- **WHEN** a photo is processed
- **THEN** its embedding is recorded as made by the image model in use

### Requirement: Project attributes
Projects SHALL carry their real-estate development name and their construction time in whole days, editable with the other project details (class-6 DuAn `du_an_bat_dong_san`, `so_ngay_thi_cong`). The project endpoints SHALL report these values, derived from the project's photos:
- `trang_thai`: published when at least one photo is;
- `da_xac_nhan_quyen_cong_bo`: true when every published photo passed the rights step;
- `ngay_xuat_ban`: the earliest publish date.

#### Scenario: Project with published photos
- **WHEN** a project has 2 published photos, published on 12/11 and 18/11
- **THEN** it reports `trang_thai` "da_xuat_ban", rights confirmed, and `ngay_xuat_ban` 12/11
