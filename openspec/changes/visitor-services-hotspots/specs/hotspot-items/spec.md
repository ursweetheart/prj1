## MODIFIED Requirements

### Requirement: Visitors still see names only
Hand-placed hotspots SHALL appear on the visitor's space page like detected ones. The visitor's hotspot card SHALL show:
- the name visitors see;
- "Không gian có món đồ này" when the hotspot is linked to a library item, otherwise "Không gian tương tự";
- when the hotspot carries a service, one small link with the service title to that service on `/dich-vu`.

The card SHALL NOT show the item's supplier, note, price or any buy or order action.

#### Scenario: Hand-placed point on a published photo
- **WHEN** a published photo gains a hand-placed point named "Đèn thả" linked to an item with a supplier
- **THEN** the visitor's card reads "Đèn thả" and "Không gian có món đồ này", and the page's data has no supplier

#### Scenario: Point with a service
- **WHEN** a detected sofa carries "Dịch vụ thiết kế phòng khách"
- **THEN** its card shows a small link "Dịch vụ thiết kế phòng khách →" to `/dich-vu#dich_vu_thiet_ke_phong_khach`, and no price

## ADDED Requirements

### Requirement: Spaces with this item for visitors
On the space page, choosing "Không gian có món đồ này" SHALL show a section listing the other published photos whose hotspots link to that item, titled with the item's name. When no other photo uses it, the section SHALL say so.

#### Scenario: Sofa used in three photos
- **WHEN** an item is linked from the current photo, two other published photos and one draft, and the visitor chooses "Không gian có món đồ này"
- **THEN** a section "Không gian có <tên món đồ>" lists the two other published photos
