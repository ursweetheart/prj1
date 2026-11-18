# Proposal

## Why

The project overview (`TONG-QUAN-DU-AN.md`, 15/11/2026) leaves four visitor-side pieces to Tùng's pages:
- **Roadmap 0.3 / issue 9.3.** The footer links "Dịch vụ và quy trình" to `/dich-vu`, which has no page.
- **Roadmap 1.9.** Items now point to a service package and the space's public data carries it, but the visitor sees neither the service nor the other spaces that use the same item.
- **Roadmap 3.1.** Three behaviour events of UC21 are still missing because they live in Tùng's components: zooming a photo (`phong_to_anh`), stepping through photos (`chuyen_anh`) and opening a hotspot (`bam_hotspot`).

The studio decided (16/11/2026) that the hotspot card may show the service as one small link, still with no price and no sales button.

## What Changes

- **`/dich-vu` page.** Lists the service packages in use, read from a new public `GET /services`, then the 5-step process, then links to the estimate, the quiz and the contact page. Without a backend (GitHub Pages) it shows the same packages from `src/data/studio.js`, marked "Thông tin mẫu". Each package has an anchor so a hotspot can link to it.
- **Hotspot card.** Shows the name; "Không gian có món đồ này" when the hotspot is linked to a library item, otherwise "Không gian tương tự"; and, when the hotspot carries a service, one small line "<service> →" to `/dich-vu#<anchor>`.
- **Spaces with this item.** On `/khong-gian/:id`, choosing "Không gian có món đồ này" opens a section listing the other published photos that use the item (`GET /items/{id}/spaces`).
- **Photo events.** `phong_to_anh` when a project photo opens full screen, `chuyen_anh` when the visitor steps to another photo there, `bam_hotspot` when a hotspot card opens. Same consent and staff rules as the other events. The trend dashboard's behaviour section gains a "Tương tác với ảnh" block: the three counts and the most opened hotspots.

## Impact

- Backend: `api.py` (`GET /services`, three event types), `pipeline/behaviour.py`, `schema.sql` (event check), tests.
- Frontend: new `ServicesView.vue` and route; `HotspotImage.vue`, `SpaceView.vue`, `ProjectView.vue`, `TrendsView.vue`, `src/api.js`, `src/data/studio.js`.
- No change to what staff see in the editor, nor to supplier and note privacy.
