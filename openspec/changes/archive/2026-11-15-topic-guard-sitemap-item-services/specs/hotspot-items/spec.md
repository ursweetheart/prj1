## ADDED Requirements

### Requirement: An item may point to a service package
An item SHALL have an optional link to one service package, which is a knowledge entry of kind "service". Staff SHALL choose it on the library page and in the hotspot editor's item form, from the service entries by title. Linking to an entry that does not exist, or is not of kind "service", SHALL be refused with 422. When a linked service entry is deleted, the item's link SHALL be cleared, and the item SHALL stay.

#### Scenario: Pick a service
- **WHEN** an architect sets "Dịch vụ thiết kế phòng khách" as the service of "Sofa vải lanh xám"
- **THEN** the item is saved with that service, and the library page shows it

#### Scenario: Not a service
- **WHEN** someone links an item to a knowledge entry of kind "faq"
- **THEN** the server answers 422 and the item is unchanged

#### Scenario: Service deleted
- **WHEN** the admin deletes a service entry that two items point to
- **THEN** both items remain, with no service

### Requirement: Hotspots carry their item's service
In the public data of a space, each hotspot SHALL carry at most one service:
- its item's service, when the item has one in use;
- otherwise the service mapped from its detected label;
- otherwise none.

A draft, waiting or switched-off service SHALL count as none. The visitor's hotspot card SHALL stay name-only.

#### Scenario: Hand-placed point gains a service
- **WHEN** a published photo has a hand-placed point "Đèn thả" linked to an item whose service is "Dịch vụ thiết kế phòng khách", which is in use
- **THEN** the space's public data for "Đèn thả" carries "Dịch vụ thiết kế phòng khách", and the visitor's card still shows only "Đèn thả"

#### Scenario: Item overrides the label
- **WHEN** a detected "bed" is linked to an item whose service is "Dịch vụ thiết kế phòng khách"
- **THEN** the hotspot carries "Dịch vụ thiết kế phòng khách", not the bedroom service

#### Scenario: Service switched off
- **WHEN** the item's service entry is switched off
- **THEN** a hand-placed point carries no service, and a detected object falls back to its label's service
