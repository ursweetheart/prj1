# Tasks

**How to verify:**
- **Backend tests:** run `docker compose up -d --build backend`, then `docker compose exec backend python -m pytest tests/<file> -q`.
- **Schema:** re-apply it with `docker compose exec -T db psql -U d3 -d d3 -q -v ON_ERROR_STOP=1 < backend/schema.sql`.
- **Frontend:** run `docker compose build web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px.
- **Test photos are restored afterwards:** tests use throw-away spaces (`test_hi_*`), or the `drafts` fixture, which restores the photo's columns and log. Test items are named `test-…` and deleted.
- **Tùng's files stay untouched:** `HotspotImage.vue`, `SpaceView.vue` and the `space-explorer` spec are not edited. Check with `git diff --stat`.

## 1. Backend

- [x] 1.1 Schema: add table `mon_do`, as in the design.

  Verify that `schema.sql` applies twice without errors.
- [x] 1.2 Create `backend/pipeline/items.py`: `key`, `create`, `update`, `delete`, `search`, `list_with_usage`, `usage`, `validate_hotspots` and `spaces_for`.

  Verify with tests:
  - `key("Sofa vải lanh  xám")` equals `key("sofa vai lanh xam")`;
  - a duplicate create or update raises `Conflict` naming the existing item;
  - deleting an item linked from 3 photos raises `InUse(3)`, and an unused one is deleted;
  - `validate_hotspots`:
    - a moved AI point keeps `label`, `bbox`, `confidence` and `nguon_tao: ai` with the new anchor;
    - a new point becomes `thu_cong` with no bbox;
    - x = 1.2, an empty name, 31 points or an unknown `mon_do_id` each raise `Invalid` (the error names the row);
    - `counts_by_category` follows the kept AI labels;
  - `spaces_for` gives published photos only unless staff.
- [x] 1.3 Endpoints:
  - `PUT /spaces/{id}/hotspots` (STAFF, review_log `hotspots`);
  - `GET/POST /items`;
  - `PATCH/DELETE /items/{id}`;
  - `GET /items/{id}/spaces`.

  Also make `relabel.py` pass only the detector's objects to the classifier.

  Verify with API tests:
  - **Access:** content and visitor get 403 on `PUT` and on every `/items` write, and anonymous 401;
  - **Save:** a `PUT` adds a hand point and moves an AI point; `GET /spaces/{id}` then shows both with their names and `nguon_tao`, a review_log row is written, and a 422 save leaves the photo unchanged;
  - **Duplicates and deletes:** duplicate names give 409 with the existing item's name, and deleting an item in use gives 409 `{so_anh}`;
  - **Public outputs:** `GET /items/{id}/spaces` as a visitor lists only published photos and has no `nha_cung_cap` or `ghi_chu`. No public response (`/spaces/{id}`, `/spaces`, `/items/{id}/spaces`) contains a test item's supplier string;
  - **`relabel.classify`** accepts a row whose hotspots include a hand-made point (the classifier stubbed).

## 2. Frontend

- [x] 2.1 In `src/api.js`, add `saveHotspots`, `searchItems`, `createItem`, `updateItem`, `deleteItem` and `itemSpaces`. Create `HotspotEditor.vue` and use it in `ReviewView.vue` instead of the inline keep/rename block:
  - click to add a point;
  - drag to move it;
  - dot buttons with arrow-key moves (Shift for bigger steps);
  - "Thêm điểm";
  - rows with the origin chip, name, item combobox with inline create, and delete;
  - "Lưu điểm nóng", with errors shown at their row.

  Verify in the browser at 1280px, as an architect, on a draft photo restored afterwards:
  - clicking adds point n+1 at the click position (within 1%);
  - dragging a point moves it;
  - arrow keys move the selected point by 1%;
  - searching an existing test item and choosing it links it;
  - "Tạo món đồ" creates and links a new one;
  - saving and reopening shows the same points, names, links and origins;
  - the visitor `/khong-gian/<id>` (after publishing the test photo, then restoring it) shows the hand point's name on Tùng's card, and the page's network responses contain no supplier;
  - a keyboard-only run (Thêm điểm → arrows → Lưu) saves the point.
- [x] 2.2 Create `ItemsView.vue` at `/quan-tri/mon-do` (STAFF):
  - search;
  - a table at 1280px and cards at 360px with photo counts;
  - an edit dialog;
  - delete with confirmation, and the "Đang dùng ở N ảnh" message with links to those photos.

  Add "Món đồ" to `SiteNav.vue` role links.

  Verify in the browser:
  - counts match the API;
  - editing a name updates the list;
  - deleting an unused item removes it;
  - deleting a used item shows the message and keeps it;
  - a content user is redirected;
  - no sideways scroll at 360px;
  - the dialog is keyboard usable (focus in, Esc closes, focus returns).

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - roadmap 1.9;
  - seq-14 status;
  - class-1's Hotspot mapping onto `space.hotspots`;
  - known issue 9 ("Hotspot chỉ có nhãn chữ");
  - the API table.

  Verify that the full backend suite shows no failures beyond the 8 known ones and that vitest passes.
