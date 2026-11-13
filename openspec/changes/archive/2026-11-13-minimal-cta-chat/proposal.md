## Why

After the minimal project grid, two elements still look like a generic app rather than the studio's site:
- the home CTA "Bạn đang có một không gian cần thiết kế?" is a grey rounded box with a filled orange button, heavier than everything around it;
- the floating "Hỏi trợ lý" button is a filled orange pill that competes with the photos on every page.

The user wants both in the minimal language of the site, with the same hover as the top bar (lift a few px, brighten to white, soft glow).

## What Changes

- **Home CTA redesigned** as an open, editorial block aligned with the project grid: hairline rule above, small eyebrow "Liên hệ", large light-weight heading, one sentence, and two text links with an arrow ("Gửi yêu cầu →", "Xem các không gian →") instead of the boxed panel and filled buttons. Heading and links side by side on desktop, stacked on phones.
- **"Hỏi trợ lý" launcher redesigned**: no orange fill; a small dark translucent pill with a hairline border, a small chat icon and light text. Hover / keyboard focus uses the top-bar effect. The open state ("Thu gọn") uses the same style.
- One shared hover utility so the CTA links, the chat launcher and the top bar stay consistent.

## Non-goals

- The chat panel itself (conversation window) — unchanged.
- The fixed header overlapping content when scrolled past the hero — separate change.
- Pages behind the CTA link (`/lien-he` does not exist yet) — separate change.

## Capabilities

### New Capabilities
- `minimal-cta-chat`: minimal home CTA and floating assistant launcher with top-bar hover.

## Impact

- `src/views/HomeView.vue` (CTA markup), `src/components/ChatWidget.vue` (launcher markup + scoped style), `src/assets/app.css` (CTA styles, shared hover utility).
