# Tasks

## 1. Backend

- [x] 1.1 `GET /services` (public): services in use, marker stripped, `mau` flag. Test: a draft service is absent; no embedding or editor field in the response.
- [x] 1.2 Events `phong_to_anh`, `chuyen_anh`, `bam_hotspot`: `Event.loai`, `schema.sql` check (applied to the running db), `behaviour.TYPES`, `overview()` adds the top hotspots. Test: stored as sent; anonymous count; overview lists the hotspot.

## 2. Frontend

- [x] 2.1 `/dich-vu` (`ServicesView.vue`, route, `STUDIO.dich_vu` fallback, hash scroll after load).
- [x] 2.2 `hotspotsOf()` passes item and service; `HotspotImage.vue` card with the item / similar link and the service link; emits `open`.
- [x] 2.3 `SpaceView.vue`: "Không gian có <món đồ>" section from `itemSpaces()`; `bam_hotspot` on open.
- [x] 2.4 `ProjectView.vue`: `phong_to_anh` on a click open, `chuyen_anh` on step.
- [x] 2.5 `TrendsView.vue`: "Tương tác với ảnh" block.

## 3. Check

- [x] 3.1 pytest (events, services) and vitest pass.
- [ ] 3.2 Browser (done 16/11 on desktop: card links, item section, /dich-vu anchor scroll, zoom/step/hotspot events stored with consent; still open: dashboard block seen as sales, 390px on a phone): footer → `/dich-vu`; hotspot card links on a published space; item section; zoom / step / hotspot events reach the dashboard with consent; 390px has no sideways scroll.


Note 3.1: on the local db the full backend suite has 55 failures that exist without this change too (no knowledge base loaded, no Vertex key, few spaces); this change adds 3 tests, all passing.
