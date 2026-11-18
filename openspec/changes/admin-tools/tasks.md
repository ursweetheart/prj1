## 1. Schema

- [ ] 1.1 In `schema.sql`:
  - `mon_do.khoang_gia`;
  - `app_user.ho_ten`;
  - `space.mo_hinh_nhung` (backfilled);
  - `du_an.du_an_bat_dong_san`, `so_ngay_thi_cong` (backfilled from `thoi_gian_thi_cong` when it is "<n> ngày");
  - the queue's `loai` CHECK + `cap_nhat_chi_muc`.

## 2. Hotspot suggestions

- [ ] 2.1 `POST /spaces/{id}/detect` (design 1), with a fake detector in tests: coordinates normalised; existing same-name hotspot filtered; 403 for visitors; rate limit.
- [ ] 2.2 `HotspotEditor.vue`: the "AI gợi ý vật thể" button, busy state, dashed suggestions with "Thêm", accepted ones become AI hotspots. Keyboard-usable.

## 3. Items

- [ ] 3.1 `khoang_gia` in the items API and edit forms, absent from the public hotspot payload. Test both.

## 4. Merge refresh

- [ ] 4.1 `merge` queues `cap_nhat_chi_muc`; the handler re-composes and re-embeds; the response carries `so_anh_cap_nhat`; `TaxonomyTree` message. Test: after the handler, no description names the source value (mocked embedder).

## 5. Accounts, models, projects

- [ ] 5.1 `ho_ten` in register, invite, `PATCH /users/{id}`, `PATCH /auth/me`, `/auth/me`, `/users`, emails; UI fields in the sign-up form and `UsersView`. Tests for each path and the length check.
- [ ] 5.2 `mo_hinh_nhung` written by `save_records`. Test.
- [ ] 5.3 The project fields in `ProjectDetailsIn` and the derived fields in the project endpoints. Tests.

## 6. Verification

- [ ] 6.1 Browser on Docker:
  - detect on a photo, accept one, save;
  - set an item's price range;
  - merge two test values and check the message and the refreshed description;
  - set a name in `UsersView`.

  Full `pytest` and `npm test` green. Remove the test data.
