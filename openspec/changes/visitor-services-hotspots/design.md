# Design

## Services source

`GET /services` (public) returns `kb_chunk` rows with `kind = 'service'` and `trang_thai = 'dang_dung'`, ordered by title: `{id, title, content, mau}`. `mau` is true when the content starts with the sample marker `[DỮ LIỆU MẪU]`; the marker is stripped from `content`, and the page shows the "Thông tin mẫu" badge instead, as on the about page. No embedding, match phrases or editor fields leave the server.

The page's anchor for a service is `slug(title)` (`src/lib/slug.js`), so the hotspot card can build the same anchor from the service title in the space data. Because the list loads after navigation, the page scrolls to the hash itself once the list is drawn (the router's `scrollBehavior` runs before the element exists).

Fallback: when `/services` fails (no backend), the page uses `STUDIO.dich_vu` from `src/data/studio.js`, which copies the three sample services and is `mau: true`.

## Hotspot card

`hotspotsOf()` passes `itemId` (`mon_do_id`) and `service` through. The card:

1. name (bold);
2. `itemId` ? "Không gian có món đồ này →" (emits `item`) : "Không gian tương tự →" (emits `similar`);
3. `service` ? a small dimmer line "<service> →" as a router link to `/dich-vu#<slug>`.

Opening a card emits `open` with the hotspot, which `SpaceView` turns into `bam_hotspot`.

## Spaces with this item

`SpaceView` keeps `itemSpaces = {item, spaces}`; on `item` it calls `GET /items/{id}/spaces`, drops the current photo, and renders a section "Không gian có <tên>" above the similar section, then scrolls to it. If the list is empty after dropping the current photo, the section says only this photo uses it and the "similar" section stays the fallback.

## Photo events

| Event | Where | `trang` | `doi_tuong` |
| :-- | :-- | :-- | :-- |
| `phong_to_anh` | ProjectView, opening the Lightbox by a click (not by a `?anh=` deep link) | `/du-an/:slug` | `<slug>/<photo no.>` |
| `chuyen_anh` | ProjectView, Lightbox ‹ › or arrow keys | `/du-an/:slug` | `<slug>/<new photo no.>` |
| `bam_hotspot` | SpaceView, a hotspot card opens | `/khong-gian/:id` | `<space id>/<item id or label slug>` |

All three fit the existing `doi_tuong` pattern `^[A-Za-z0-9_/-]{1,100}$`, so the table gains no column; only the `loai` check and the `Literal` grow. `trackEvent()` already skips staff and applies consent.

`behaviour.overview()` adds `anh: {phong_to_anh, chuyen_anh, bam_hotspot}` (consented counts are already in `dong_y` / `an_danh` once the types are in `TYPES`) and `hotspot`: top 10 `bam_hotspot` objects with counts. The dashboard reads the hotspot object as "photo #id · label".
