# Proposal

## Why

Hotspots today are whatever the object detector found at upload: 153 photos and about 1,200 objects ("chair" 414, "couch" 105, …). On the review page an architect can only rename one or drop it. They cannot:
- move a point the detector put in the wrong place;
- add the pendant lamp or rug it missed;
- say *which* sofa it is.

The design asks for more:
- **Seq-14 ("Gắn hotspot món đồ"):** an architect clicks a position on the photo, chooses or creates an item with its style, material, colour and supplier, and the hotspot is saved with its coordinates, the item and whether a person or the AI created it.
- **Class-1:** `Hotspot (toa_do_x, toa_do_y, nguon_tao, do_tin_cay)` linked to `MonDo (ten, phan_loai, kieu_dang, vat_lieu, mau_sac, …)`.
- **Roadmap 1.9:** "thêm điểm bằng tay, kéo vị trí; bảng MonDo".

## What Changes

- **Hotspot editing on the review page** (`/quan-tri`, architects, lead architect, admin):
  - click on the photo to add a point;
  - drag a point to move it, or select it and use the arrow keys;
  - delete a point;
  - edit each point's name, which visitors see;
  - link a point to an item from the library.

  Points the detector made keep their detection box and confidence, and are marked "AI". Points added by hand are marked "Thủ công". The whole list is saved at once and logged in the review log.
- **An item library (MonDo)** with name, type (e.g. sofa, đèn thả), style, material, colour, supplier and a staff note.
  - **Choose or create inline:** in the hotspot editor, search existing items or create one without leaving the photo (seq-14 step 12).
  - **A library page `/quan-tri/mon-do`:** list and search items with how many photos use each, edit them, and delete one that no photo uses (an item in use answers 409 with its usage).
  - **Material suggestions** come from the taxonomy's "Vật liệu" values, but any text is allowed.
- **"Spaces with this item":** `GET /items/{id}/spaces` lists the photos whose hotspots link to an item. Visitors see published photos only, and the item's name and type, never its supplier or note. Staff see all photos. It lets the visitor side ask "show spaces with this sofa" later, without changing it now.
- **The visitor's space page is unchanged.**
  - Its card still shows only the point's name and "Không gian tương tự", as Tùng's `space-explorer` spec requires.
  - Hand-placed points appear there like detected ones, because they are stored in the same form.
  - The supplier and staff note are never in any public response.

**Decision taken with the user:** staff side only. Tùng's `HotspotImage.vue`, `SpaceView.vue` and the `space-explorer` spec are not touched.

## Capabilities

### New Capabilities
- `hotspot-items`: editing hotspots by hand (add, move, delete, rename, link), the item library and its management, and listing the spaces that use an item.

### Modified Capabilities
None. `space-explorer` keeps its name-only card. `photo-review` keeps its review flow; the old "keep and rename detected objects" save still works and becomes a subset of the new editor. `assistant-knowledge` keeps its rule that sofa and TV hotspots link to a service by their detected label; hand-placed points have no detected label, so they link to no service.

## Impact

- **Backend:**
  - new `backend/pipeline/items.py` (library rules and hotspot validation);
  - `backend/api.py`:
    - `PUT /spaces/{id}/hotspots`;
    - `GET/POST /items`, `PATCH/DELETE /items/{id}`;
    - `GET /items/{id}/spaces`;
  - new `backend/tests/test_hotspot_items.py`.
- **Schema:**
  - table `mon_do`;
  - each object in `space.hotspots.objects` may carry `nguon_tao` ('ai' | 'thu_cong') and `mon_do_id`. No migration: objects without them are AI-made and unlinked.
- **Frontend:**
  - `src/api.js`;
  - `src/views/ReviewView.vue` (the hotspot editor);
  - new `src/components/HotspotEditor.vue`;
  - new `src/views/ItemsView.vue`;
  - the route;
  - "Món đồ" in `SiteNav.vue` role links.
- **Out of scope:**
  - re-running the object detector from the review page (the detector's points at upload are the AI suggestions of seq-14 steps 6–9);
  - showing items, suppliers or prices to visitors;
  - linking items to service packages;
  - photos of items;
  - importing a supplier catalogue.
