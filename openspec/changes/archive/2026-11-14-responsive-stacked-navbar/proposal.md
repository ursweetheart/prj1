## Why

On narrow screens the header broke: `.nav-in` was a `1fr auto 1fr` grid, and once the centre column (`.nav-center`) was hidden, the account/language/burger cluster fell into the middle column while the 72px logo and 36px wordmark kept their desktop size, so "Đăng nhập" was drawn on top of "D3 STUDIO". The product owner also asked for a header that reads as a brand statement on phones: a large logo, no burger menu, every item visible and stacked under the brand, and a smooth "lift and brighten" hover on each item.

## What Changes

- **Stacked header below 1024px**: brand centred on the first row, the main links ("Dự án", "Về chúng tôi", "Liên hệ") on the next row, account links + "Vi | En" on the last row; rows wrap and stay centred down to 320px with no horizontal scroll.
- **BREAKING (for `minimalist-architectural-navbar`)**: the burger button and the mobile drawer (`.nav-sheet`) are removed; all items are always visible instead.
- **Larger, fluid brand on small screens**: wordmark `clamp(28px, 9vw, 48px)`, mark `clamp(36px, 11.5vw, 62px)`.
- **Cropped logo asset**: new `public/img/logo_mark.png` (the "B" mark with the transparent padding of `logo_xoa_nen.png` cut away), so the mark is sized against the wordmark instead of against empty space; the original file is kept.
- **Desktop bar from 1024px**: three-column grid `minmax(max-content, 1fr) auto minmax(max-content, 1fr)` so neither side column can shrink under its content; the original large sizes (36px wordmark) from 1280px.
- **Hover / focus feedback**: brand, links, account buttons and language buttons lift 3px (brand 4px), turn full white and gain a soft glow on a 0.45s `cubic-bezier(0.22, 1, 0.36, 1)` curve; the same on `:focus-visible`; the active link keeps its red with a red glow.
- **Legibility over bright hero photos**: stronger top gradient and a soft dark text/drop shadow under header text and brand.

## Capabilities

### New Capabilities
- `responsive-site-header`: layout of the site header per viewport range (stacked under 1024px, three-column bar above), brand sizing and asset, hover/focus motion, and legibility over the hero image.

### Modified Capabilities

None archived yet under `openspec/specs/`. This change supersedes the "responsive burger menu / mobile drawer" goal of the unarchived change `minimalist-architectural-navbar`.

## Impact

- `src/components/SiteNav.vue`: burger button, `.nav-sheet` drawer and the `open` state removed.
- `src/components/BrandMark.vue`: points to `img/logo_mark.png`.
- `src/assets/app.css`: header section rewritten (mobile-first stacked layout, 600 / 1024 / 1280px breakpoints, hover transitions, gradient and shadows); `.nav-burger` / `.nav-sheet` rules removed.
- `public/img/logo_mark.png`: new asset.
- The header is `position: fixed` and is now about 165–210px tall under 1024px; pages without a full-bleed hero (e.g. `/cong-trinh`) are covered by it at the top. That overlap already existed at 96px and is left to a follow-up (see design).
