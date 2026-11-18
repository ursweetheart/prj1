## 1. Schema

- [x] 1.1 In `schema.sql`:
  - `mon_do.khoang_gia`;
  - `app_user.ho_ten`;
  - `space.mo_hinh_nhung` (backfilled);
  - `du_an.du_an_bat_dong_san`, `so_ngay_thi_cong` (backfilled from `thoi_gian_thi_cong` when it is "<n> ngày");
  - the queue's `loai` CHECK + `cap_nhat_chi_muc`.

## 2. Hotspot suggestions

- [x] 2.1 `POST /spaces/{id}/detect` (design 1), with a fake detector in tests: coordinates normalised; existing same-name hotspot filtered; 403 for visitors; rate limit.
- [x] 2.2 `HotspotEditor.vue`: the "AI gợi ý vật thể" button, busy state, dashed suggestions with "Thêm", accepted ones become AI hotspots. Keyboard-usable.

## 3. Items

- [x] 3.1 `khoang_gia` in the items API and edit forms, absent from the public hotspot payload. Test both.

## 4. Merge refresh

- [x] 4.1 `merge` queues `cap_nhat_chi_muc`; the handler re-composes and re-embeds; the response carries `so_anh_cap_nhat`; `TaxonomyTree` message. Test: after the handler, no description names the source value (mocked embedder).

## 5. Accounts, models, projects

- [x] 5.1 `ho_ten` in register, invite, `PATCH /users/{id}`, `PATCH /auth/me`, `/auth/me`, `/users`, emails; UI fields in the sign-up form and `UsersView`. Tests for each path and the length check.
- [x] 5.2 `mo_hinh_nhung` written by `save_records`. Test.
- [x] 5.3 The project fields in `ProjectDetailsIn` and the derived fields in the project endpoints. Tests.

## 6. Verification

- [x] 6.1 Browser on Docker:
  - detect on a photo, accept one, save;
  - set an item's price range;
  - merge two test values and check the message and the refreshed description;
  - set a name in `UsersView`.

  Full `pytest` and `npm test` green. Remove the test data.

## Results (2026-11-18)

- **Note on the task list:** the queue has no `loai` CHECK (handlers are registered in code), so 1.1's last item became registering the `cap_nhat_chi_muc` handler in `pipeline/space_knowledge.py`.
- **Browser, headless:**
  - "AI gợi ý vật thể" on a draft ran the local detector (CPU) and showed 5 dashed boxes with names and confidence; "Thêm" added a point marked "AI", and saving stored it with source AI, `nguon_ai = yolo_theo_yeu_cau` and its confidence;
  - an item's "12 – 18 triệu" showed in the staff item list and not in the public payload;
  - merging a throw-away material value in the taxonomy tree said "Đã gộp «Đá Zzat cũ» vào «Gỗ Zzat mới»; chỉ mục đang được cập nhật cho 1 ảnh.", and within seconds the photo's description no longer named the old value;
  - the admin set a full name in the account list, and the user saw it and changed it at /dang-nhap.
- **Fix found while checking:** the own-name field filled before the account had loaded; it now updates once the account arrives.
- **Cleanup:** the photo's hotspots were restored, the test values removed (the photo's description refreshed again), and the temporary accounts deleted.
- **Tests:** `pytest` 544 passed (3 known environment failures); `npm test` 88 passed.
