## Purpose

The site header at every screen width: a stacked, burger-free layout on small screens and a one-row bar from 1024px, the brand's size and asset, lift-and-brighten feedback that never sticks on touch screens, legibility over the hero photo, and staff links grouped so the header never runs out of room.

## ADDED Requirements

### Requirement: Header items never overlap
The site header SHALL lay out the brand, the main links, the account links and the language switcher without any two of them overlapping, and without causing horizontal page scroll, at every viewport width from 320px upward.

#### Scenario: Narrow window
- **WHEN** a visitor opens the home page in a window 320px to 1023px wide
- **THEN** the brand, the main links and the "Đăng nhập" / "Vi | En" items do not overlap each other
- **AND** the document is not wider than the viewport

#### Scenario: Desktop window
- **WHEN** a visitor opens the home page in a window 1024px or wider
- **THEN** the brand, the centred main links and the right-hand account/language cluster each stay within their own column

### Requirement: Stacked header on small screens
Below 1024px the header SHALL show all navigation items without a menu button, stacked and centred: the brand on the first row, the main links on the next, and the account links with the language switcher on the last. Rows MAY wrap but SHALL stay centred.

#### Scenario: Phone layout
- **WHEN** a visitor opens any page on a 390px wide screen
- **THEN** no burger or menu button is rendered
- **AND** the "D3 STUDIO" brand is centred at the top, "Dự án", "Về chúng tôi", "Liên hệ" are on a row below it, and "Đăng nhập" and "Vi | En" are on a row below that

#### Scenario: Desktop layout
- **WHEN** the viewport is 1024px or wider
- **THEN** the header is a single row with the brand on the left, the main links centred and the account/language cluster on the right

### Requirement: Prominent, balanced brand
On small screens the brand SHALL scale with the viewport and be larger than the brand of the desktop bar at 1024–1279px. The logo mark SHALL be rendered from an asset without surrounding transparent padding, so its visible height is in proportion to the wordmark.

#### Scenario: Brand grows with the screen
- **WHEN** the viewport grows from 320px to 1023px
- **THEN** the wordmark grows from about 28px up to at most 48px and the mark grows with it

#### Scenario: Mark matches the wordmark
- **WHEN** the header renders at any width
- **THEN** the visible "B" mark is at least as tall as the capital letters of the wordmark and sits close to it, with no wide empty gap between them

### Requirement: Lift-and-brighten feedback on header items
The brand, each main link, each account link or button and each language button SHALL, on pointer hover and on keyboard focus (`:focus-visible`), move up by a few pixels and become brighter with a smooth eased transition. The active link SHALL keep its red colour while hovered.

#### Scenario: Hovering a link
- **WHEN** the pointer moves over "Về chúng tôi"
- **THEN** the link moves up 3px, its colour becomes full white and it gains a soft light glow, animating over about 0.45s

#### Scenario: Keyboard focus
- **WHEN** a keyboard user tabs onto a header link
- **THEN** it shows the same lift and brightening as on hover

#### Scenario: Reduced motion
- **WHEN** the visitor's system requests reduced motion
- **THEN** the hover state is applied without a visible animation

### Requirement: Header readable over the hero photo
Header text and the brand SHALL remain readable over bright areas of the hero image, in both the normal and the hovered state.

#### Scenario: Bright ceiling behind the header
- **WHEN** the hero photo behind the header is bright (for example a lit ceiling)
- **THEN** a darkening gradient and a soft dark shadow keep the white header text legible
- **AND** the hover glow is layered on top of that shadow rather than replacing it

### Requirement: Staff links grouped
A signed-in user with one staff link SHALL see it in the header as a plain link. A user with two or more staff links SHALL see one "Quản trị" button instead, which opens a list of those links. The list SHALL close on Esc (returning focus to the button), on a click outside it and on navigation. The button SHALL state whether the list is open, and SHALL be marked while the user is on one of those pages.

#### Scenario: Lead architect at 1280px
- **WHEN** a lead architect (Duyệt, Phân loại, Đơn giá, Khách hàng, Xu hướng) opens any page in a 1280px window
- **THEN** the header shows "Bộ sưu tập", "Quản trị", "Đăng xuất" and "Vi | En" in one row with no overlap and no horizontal scroll

#### Scenario: Open and close the menu
- **WHEN** they press "Quản trị", then press Esc
- **THEN** the five links are listed, then the list closes and focus is back on "Quản trị"

#### Scenario: Sales at 360px
- **WHEN** a sales user opens a page on a 360px screen
- **THEN** every header item is visible, nothing overlaps and the page does not scroll sideways

### Requirement: No stuck hover on touch screens
On devices without a hovering pointer, tapping a header item SHALL NOT leave it in the lifted, brightened state. Keyboard focus SHALL keep that state on every device.

#### Scenario: Tap on a phone
- **WHEN** a visitor taps "Dự án" on a touch screen and comes back to the previous page
- **THEN** no header item is shown lifted or glowing
