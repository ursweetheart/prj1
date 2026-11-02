## ADDED Requirements

### Requirement: Minimal home CTA
The home CTA SHALL be an open block without a background box or filled buttons: a hairline rule, the eyebrow "Liên hệ", the heading "Ý tưởng về một không gian cá nhân hoá, hãy để lại thông tin", one sentence, and the text links "Gửi yêu cầu" (to `/lien-he`) and "Xem các không gian" (to `/cong-trinh`), each followed by an arrow. Its left and right edges SHALL align with the project grid above it.

#### Scenario: Desktop layout
- **WHEN** the viewport is 1280px wide
- **THEN** the heading and sentence are on the left, the two links on the right, and there is no panel background

#### Scenario: Phone layout
- **WHEN** the viewport is 390px wide
- **THEN** the links are stacked below the sentence and the page has no horizontal scroll

### Requirement: Minimal assistant launcher
The floating assistant launcher SHALL be a small translucent dark pill with a hairline border, a chat icon and light text ("Hỏi trợ lý", or "Thu gọn" while the panel is open), without the orange fill.

#### Scenario: Launcher over a photo
- **WHEN** the launcher sits over the hero photo
- **THEN** its text is readable and it has no orange background

### Requirement: Top-bar hover on CTA links and launcher
On hover and keyboard focus, the CTA links and the launcher SHALL lift by 3px, turn white and glow softly, with the same timing curve as the top-bar links. With reduced motion they SHALL glow without moving.

#### Scenario: Hover the launcher
- **WHEN** the visitor hovers "Hỏi trợ lý"
- **THEN** it moves up 3px, its text turns white with a soft glow and its border brightens
