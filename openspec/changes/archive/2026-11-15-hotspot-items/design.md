# Design

## Context

- **Storage.** `space.hotspots` is jsonb `{objects: [...], inference_time_ms, counts_by_category}`. Each object is `{label (COCO), label_vi, confidence, bbox {x_min,y_min,x_max,y_max}, hotspot_anchor [x, y]}`, normalised 0–1. The detector (`furniture_detector.py`) writes it at upload; `relabel.py` reads it and validates it against the detector's schema. 153 photos have hotspots.
- **Readers:**
  - **Visitors:** `GET /spaces/{id}` passes the objects through `with_services()`, which adds `service` for sofa / TV / bed labels. `hotspotsOf()` in `src/api.js` maps `hotspot_anchor` and `label_vi || label` to the visitor card. That card is Tùng's `HotspotImage.vue` and `space-explorer` spec: name only.
  - **Staff:** the review page (`ReviewView.vue`, ours) opens a photo's objects, lets staff rename or drop them, and saves through `PATCH /spaces/{id}` with `hotspots: [{index, label_vi}]` (keep-only, coordinates fixed). That save is logged as review_log action `hotspots`.
- **Taxonomy materials:** Gỗ, Đá, Kính, Kim loại, Vải, Mây tre, Da, Gốm sứ.
- **Seq-14:** open photo → existing hotspots and item catalogue → (optional AI suggestions) → click a position → item picker (style, material, colour, supplier) → choose or create → save (coordinates, item id) → record origin "thủ công / AI".

## Goals / Non-Goals

**Goals:**
- Add, move, delete, rename and link hotspots.
- An item library that can be searched, created inline and edited.
- Spaces listed by item.
- No change to the visitor page or its data shape.

**Non-Goals:**
- Re-running detection from the UI.
- Showing items to visitors.
- Item photos.
- Prices and services per item.
- Bulk tagging across photos.

## Decisions

### 1. Keep hotspots in `space.hotspots`, add two fields
Each object may gain `nguon_tao: 'ai' | 'thu_cong'` and `mon_do_id: int | null`.
- **Hand-made objects** are `{label_vi, hotspot_anchor, nguon_tao: 'thu_cong', mon_do_id}`, with no `label`, `bbox` or `confidence`.
- **Missing `nguon_tao`** means `ai`, so no migration is needed.

**Why not a `hotspot` table as in class-1:**
- every reader (the visitor page, `with_services`, `relabel.py`, the review page) already reads this JSON;
- a table would need all of them changed, including Tùng's visitor page;
- the class's fields (x, y, origin, confidence, item) map one-to-one onto the object.

The design records this as the mapping of class-1's `Hotspot`.

### 2. Table `mon_do`
```sql
CREATE TABLE IF NOT EXISTS mon_do (
  id serial PRIMARY KEY,
  ten text NOT NULL CHECK (length(ten) BETWEEN 1 AND 120),
  ten_khoa text NOT NULL UNIQUE,      -- folded name (taxonomy.fold, words joined by one space): the duplicate check
  phan_loai text CHECK (length(phan_loai) <= 60),   -- type: Sofa, Đèn thả, Bàn ăn…
  kieu_dang text CHECK (length(kieu_dang) <= 60),   -- style
  vat_lieu text CHECK (length(vat_lieu) <= 60),
  mau_sac text CHECK (length(mau_sac) <= 40),
  nha_cung_cap text CHECK (length(nha_cung_cap) <= 120),   -- staff only
  ghi_chu text CHECK (length(ghi_chu) <= 500),             -- staff only
  tao_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  cap_nhat_boi int REFERENCES app_user(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```
**Usage** is computed: `SELECT count(DISTINCT s.id) FROM space s, jsonb_array_elements(s.hotspots->'objects') o WHERE (o->>'mon_do_id')::int = $1`. At 153 photos this is instant; an index can come later.

### 3. `pipeline/items.py`
- **`key(name)`:** `" ".join(re.findall("[a-z0-9]+", taxonomy.fold(name)))`, the same rule as the knowledge-gap groups.
- **Library operations:**
  - `create`, `update` (409 `Conflict(existing)` on a duplicate key);
  - `delete` (409 `InUse(n)`);
  - `search(q, limit)` by key substring over name, type and material;
  - `list_with_usage()`;
  - `usage(id)`.
- **`validate_hotspots(conn, current_objects, edited)`** turns the editor's list into the objects to store:
  - **An edited point `{index?, x, y, label_vi, mon_do_id?}`:**
    - with an `index` of a current AI object: copy that object (`label`, `bbox`, `confidence`), set `hotspot_anchor` to `[x, y]` and set `label_vi`;
    - without an index: build a `thu_cong` object.
  - **Checks:** 0 ≤ x, y ≤ 1; names 1–120 characters; at most 30 points; every `mon_do_id` must exist. Anything else raises `Invalid`, which becomes 422.
  - **Moving an AI point keeps `nguon_tao: 'ai'`.** The box stays as detected, so it describes the detection, not the new position.
  - **`counts_by_category`** is recomputed from the kept AI labels, so the detector's counts stay truthful.
- **`spaces_for(conn, item_id, staff)`:** `[{id, relative_path, space_type, design_style, review_status?}]`, published only unless staff.

### 4. API (`STAFF` = architect, lead_architect, admin)
| Endpoint | Who | What |
| :-- | :-- | :-- |
| `PUT /spaces/{id}/hotspots` `{hotspots: [...]}` | STAFF | replace the photo's objects (validated); review_log `hotspots` with `{truoc, sau, thu_cong, lien_ket}` counts |
| `GET /items?q=&limit=` | STAFF | search, with `so_anh` usage |
| `POST /items` | STAFF | create; 409 on duplicate (body names the existing item) |
| `PATCH /items/{id}` | STAFF | edit; 409 on duplicate; 404 |
| `DELETE /items/{id}` | STAFF | 204; 409 `{so_anh}` when in use; 404 |
| `GET /items/{id}/spaces` | public | visitors get `{mon_do: {id, ten, phan_loai}, spaces: [published]}`; staff get all photos and the full item |

The old `PATCH /spaces/{id}` with `hotspots: [{index, label_vi}]` stays for compatibility. The new editor uses `PUT`.

### 5. Editor (`HotspotEditor.vue`, used by `ReviewView.vue`)
It replaces the current inline keep/rename block.
- **The photo**, at its natural ratio, shows numbered dots.
  - **Mouse:** clicking empty photo area adds a point there. A dot can be dragged with pointer events, within the photo's bounds.
  - **Keyboard:** each dot is a button; selecting it lets the arrow keys move it by 1% (10% with Shift). "Thêm điểm" adds a point at the centre and selects it.
- **Below the photo, one row per point:** number, an "AI" / "Thủ công" chip, the name input, the item picker and a delete button.
- **The item picker** is a text input with `role="combobox"` and a listbox of `GET /items?q=` results, debounced at 200 ms, plus "Tạo món đồ «…»" when nothing matches exactly.
  - Creating opens a small inline form (type, style, material with taxonomy suggestions in a `datalist`, colour, supplier). On save it links the item.
  - When the point's name is empty or still the detector's label, linking fills it with the item's type, never the supplier.
- **"Lưu điểm nóng"** sends `PUT`. Errors show next to the field (422 detail `loc` gives the row).

### 6. Library page `ItemsView.vue` (`/quan-tri/mon-do`, STAFF)
- **A table** at ≥ 760px and stacked cards below: name, type, material, colour, supplier, photo count.
- **Search,** and editing in a dialog with the same fields.
- **Delete** asks for confirmation. When the item is in use, a 409 shows "Đang dùng ở N ảnh", with the photo list from `GET /items/{id}/spaces`.
- **Nav:** "Món đồ" in `SiteNav.vue` role links for STAFF.

## Risks / Trade-offs

- **[JSON instead of a table]** → Hotspots cannot be joined by SQL foreign key, so item usage is a JSON scan and deleting an item cannot cascade. That is why delete is refused while in use. Fine at this scale; the mapping is documented.
- **[`relabel.py` validates stored hotspots against the detector schema]** → It only reads them (to give the classifier the detected objects), but `FurnitureDetectionResult.model_validate` needs `label`, `bbox` and `confidence`, which hand-made points lack. `relabel.py` (our script) will pass only the detector's objects (`nguon_tao` absent or `ai`). No other code validates stored hotspots, and `with_services` already uses `o.get("label")`, so hand-made points simply get no service.
- **[Moved AI point with an old box]** → The box is kept only as detection evidence. The anchor is what is drawn.
- **[Supplier leaks]** → It lives only in `mon_do` and is returned only to staff endpoints. Public `GET /spaces/{id}` carries `mon_do_id` only, and a test checks the public outputs.

## Migration Plan

- Apply `schema.sql` (the `mon_do` table). Existing hotspots are valid as they are.
- **Rollback:** the old PATCH path still works, and the extra fields in the JSON are ignored by every reader.
