## Context

The current navbar in `SiteNav.vue` employs a dark color palette with a standard CTA button and custom SVG logo. To align with top-tier architectural studio branding (as requested in reference image 1), we are pivoting to a crisp, ultra-minimalist light layout featuring a signature 3x3 dot matrix logo, right-aligned navigation items, bold red active states (`#C01919`), and a bilingual language selector.

## Goals / Non-Goals

**Goals:**
- Implement interactive 3x3 red dot matrix brand logo in `BrandMark.vue`.
- Redesign `SiteNav.vue` to position logo on the left and right-align links ("Dự án", "D3er", "Tin tức", "Liên hệ") + language switcher ("VI | EN").
- Highlight the active page link with bold red accent typography (`#C01919`).
- Ensure high contrast, clean architectural line separators, and frosted glass scroll transition.
- Responsive burger menu preserving the minimalist architectural aesthetic on mobile devices.

**Non-Goals:**
- Full website internationalization (i18n translation framework installation is non-goal for this navbar design change, only the UI toggle state).

## Decisions

- **Decision 1: SVG-based 3x3 Dot Matrix**: Implement `BrandMark.vue` using pure SVG 3x3 grid circles (`<circle>`) with CSS transition effects for micro-interactions on hover.
  - *Rationale*: Lightweight, crisp rendering at all screen pixel densities, zero third-party library dependencies.
- **Decision 2: Light Architectural Palette**: Use a clean white/off-white translucent background (`rgba(255, 255, 255, 0.92)`) with a subtle 1px border (`#eee`) and blur backdrop.
  - *Rationale*: Matches the exact high-end architectural gallery aesthetic of the reference image.
- **Decision 3: Right-aligned Nav Cluster**: Group navigation links and language switcher in a right-aligned flex layout with clean sans-serif typography (`letter-spacing: 0.02em`).

## Risks / Trade-offs

- **[Risk]** Dark hero section contrast overlap.
  - **Mitigation**: Use a crisp frosted glass bar with subtle bottom border so dark page contents behind the header remain perfectly readable without clutter.
