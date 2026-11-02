## Context

`SiteNav.vue` renders a transparent, `position: fixed` header over the home hero photo. Its inner row `.nav-in` was a `1fr auto 1fr` grid with three children: `.nav-left` (brand), `.nav-center` (main links, hidden under 900px) and `.nav-right` (account, language, burger). Brand sizes were fixed at 72px (mark) and 36px (wordmark). The mark image `logo_xoa_nen.png` is 500×500 but its visible "B" only fills about 221×250px in the middle (alpha bounding box x 150–371, y 126–375), so the mark always rendered at about half its box height with wide empty sides.

Requested by the product owner on 2026-10-31 after seeing the overlap on a ~760px wide window: fix the overlap first, then make the brand larger on small screens, drop the burger, stack everything under the brand, and add a smooth lift-and-brighten hover.

## Goals / Non-Goals

**Goals:**
- No overlap and no horizontal scroll in the header from 320px to wide desktop.
- Below 1024px: no burger, all items visible, stacked and centred under a large brand.
- Brand mark visually balanced with the wordmark at every size.
- Smooth hover and keyboard-focus feedback (lift + brighten) on every header item.
- Header text readable over the bright ceiling area of the hero photo.

**Non-Goals:**
- Content offset under the fixed header on pages without a hero (`/cong-trinh`, `/quan-tri`, ...).
- Collapsing or shrinking the header on scroll.
- Real language switching (Vi/En stays a UI toggle, as before).
- Changing the header colour scheme or the link set.

## Decisions

- **Mobile-first flex column, grid only from 1024px.** Under 1024px `.nav-in` is `flex-direction: column; align-items: center`, which stacks the three existing children in DOM order without changing the template. From 1024px it switches to a grid. *Alternative*: keep the grid and hide items per breakpoint, which is what caused the overlap once a column was empty.
- **`minmax(max-content, 1fr)` for the desktop side columns.** Plain `1fr` lets a column shrink below its content so the brand can spill into the centre; `minmax(max-content, 1fr)` keeps both sides at least content-wide while still centring the links when space allows. Measured at 1024px for a guest: brand ends at 264px, links span 378–631px, right cluster starts at 647px.
- **Breakpoints 600 / 1024 / 1280.** 600px only widens spacing and link size; 1024px is the smallest width where brand + 3 links + account + language fit on one row with margin (≈780px needed for a guest); 1280px restores the original large sizes.
- **Fluid brand via `clamp()`** (`9vw` wordmark, `11.5vw` mark) rather than more breakpoints: at 320px the brand fits inside the 272px content box; at 768px it reaches the 48px / 62px caps.
- **Crop the logo asset instead of compensating in CSS.** Negative margins or `object-view-box` would tie the layout to the padding of one file (and `object-view-box` is not supported in Firefox). A tightly cropped `logo_mark.png` (230×258, 4px safety margin) makes `height` mean the height of the visible mark. The original is kept because other places may reference it.
- **Hover = `transform` + `color` + `text-shadow` / `filter` only.** These are cheap to animate, so the lift stays smooth; one shared easing `cubic-bezier(0.22, 1, 0.36, 1)` over 0.45s gives a quick start and a soft landing. Inline links get `display: inline-block` so `transform` applies. The glow is layered on top of the dark legibility shadow rather than replacing it, so a hovered item stays readable on a bright background. The existing `prefers-reduced-motion` rule already cuts transitions to 1ms, and motion happens only on interaction, which matches the client survey answer (question 30) of no load or scroll animation.
- **Legibility**: the gradient behind the header goes from `rgba(0,0,0,.72)` through `.45` at 55% to transparent (was `.6` → 0), plus `text-shadow: 0 1px 10px rgba(0,0,0,.45)` on `.nav-in` and a matching `drop-shadow` on the brand.

## Risks / Trade-offs

- **[Risk]** The stacked header is 165–210px tall under 1024px and covers more of the hero photo. → Mitigation: it is transparent with a fading gradient, so the hero stays visible behind it. A collapse-on-scroll can be added later if needed.
- **[Risk]** The fixed header overlaps the top of pages without a hero (already the case at 96px, now taller on mobile). → Follow-up: add a header-height offset (CSS variable) to those pages, outside this change.
- **[Risk]** A signed-in editor or sales user adds "Duyệt" / "Khách hàng" / "Đăng xuất" to the right cluster; at 1024px this is estimated at ≈1007px of content, close to the limit. → Not yet verified in the browser (task 5.4); fallback is raising the one-row breakpoint or letting the account cluster wrap.
- **[Trade-off]** Without a burger every item is always on screen on phones. Fine for today's 3 links + 2 account items; if the link set grows, the stacked rows get taller.
