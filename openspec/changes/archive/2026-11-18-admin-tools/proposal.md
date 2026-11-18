# Proposal

## Why

The admin-side diagrams have steps and attributes the code lacks:
- **seq-14 steps 6-9:** the hotspot editor can ask the AI to suggest objects on demand, and returns boxes with confidence.
- **class-6 MonDo:** items have a price range (`khoang_gia`).
- **seq-15 steps 20 and 22:** merging two taxonomy values queues a task that refreshes the labels in the search index.
- **class-6 attributes with no counterpart:**
  - NguoiDung `ho_ten`;
  - the vectors' `ten_mo_hinh` (embedding model name);
  - DuAn `du_an_bat_dong_san`, `so_ngay_thi_cong` (a number of days), `trang_thai`, `da_xac_nhan_quyen_cong_bo` and `ngay_xuat_ban`.

## What Changes

- **"AI gợi ý vật thể" in the hotspot editor:**
  - runs the local furniture detector on the photo;
  - shows each proposed object as a dashed marker with its name and confidence;
  - the architect accepts a suggestion (it becomes a hotspot with source "AI") or ignores it;
  - nothing is saved until the editor saves, as today.
- **Item price range:** items gain an optional `khoang_gia` text, edited in the item box and shown to staff.
- **Merge refreshes the index:**
  - after a merge, a queued task refreshes the affected photos' search-index entries (the assistant's photo descriptions and their embeddings);
  - the merge answer says the refresh is queued.
- **Class attributes:**
  - accounts get a full name (`ho_ten`): set at sign-up, by invitation, by the admin, or by the user;
  - photo embeddings and photo descriptions record the model that made them;
  - projects get `du_an_bat_dong_san` (the real-estate development) and `so_ngay_thi_cong` (whole days), editable with the other details;
  - `GET /projects` / `GET /projects/{slug}` report `trang_thai` (`da_xuat_ban` / `chua_xuat_ban`), `da_xac_nhan_quyen_cong_bo` and `ngay_xuat_ban`, derived from the project's photos.

## Capabilities

### New Capabilities
- `admin-tools`: on-demand object suggestions in the hotspot editor, the item price range, the queued index refresh after a merge, account full names, embedding model names and the project attributes.

### Modified Capabilities
(none)

## Impact

- **Backend:**
  - `api.py`: `POST /spaces/{id}/detect`, items, projects, merge;
  - `auth.py` and `pipeline/accounts.py`: `ho_ten`;
  - `pipeline/taxonomy_admin.merge` + a `cap_nhat_chi_muc` task handler in `pipeline/intake.py`;
  - `pipeline/store.py`: model name;
  - `schema.sql`.
- **Frontend:** `HotspotEditor.vue`, `ItemsView.vue` / the item box, `UsersView.vue`, the sign-up form, `TaxonomyTree.vue` (merge message).
- **Depends on:** `labelling-queue-feedback` (queue) and `publishing-workflow` (photo descriptions, `ngay_xuat_ban`).
