## Context

- Top-bar hover (`src/assets/app.css`, "Hover / keyboard focus" block): `translateY(-3px)`, colour → `#fff`, `text-shadow: 0 0 14px rgba(255,255,255,.55)`, 0.45s `cubic-bezier(0.22, 1, 0.36, 1)`.
- Home CTA (`HomeView.vue`): `.panel` box + `.btn-primary` / `.btn-secondary`.
- Chat launcher (`ChatWidget.vue`): `.btn.btn-primary.chat-fab`, fixed bottom-right, text "Hỏi trợ lý" / "Thu gọn".
- Project grid above the CTA: container max 1120px, light-weight display headings, faint meta text.

## Decisions

### Shared hover utility `.glow-hover`
A class with the same transition, lift, colour and text-shadow as the top bar, plus an optional `box-shadow` glow for elements that have a border (launcher). The top-bar rules stay as they are (they are already tuned and tested); the new class copies their values so the three places look identical. `prefers-reduced-motion`: no lift, glow only.

### CTA: open editorial block
```
──────────────────────────────────────────────── (hairline)
LIÊN HỆ
Bạn đang có một không gian          Gửi yêu cầu  →
cần thiết kế?                       Xem các không gian  →
Để lại thông tin, kiến trúc sư D3 Studio sẽ liên hệ với bạn.
```
- Same container as the project grid (`.projects`-width, 1120px) so edges line up.
- Heading: display font, weight 300–400, `clamp(28px, 3.4vw, 46px)`, `--ink`.
- Links: 17–19px, `--ink-2`, arrow that moves 4px right on hover, thin underline on hover; class `.glow-hover`.
- ≥ 900px: two columns (text left, links right, bottom-aligned); below: stacked.
- No background box, no filled buttons.

### Chat launcher: minimal pill
- Background `rgba(20,20,19,.45)` + `backdrop-filter: blur(8px)`, 1px border `rgba(255,255,255,.28)`, radius pill, padding 10px 16px, 14px text `rgba(255,255,255,.88)`, small 16px outline chat icon.
- Readable on both light photos and the dark page thanks to the translucent dark fill and text-shadow.
- Hover / focus-visible: `.glow-hover` (lift 3px, white text, text glow) + border to `rgba(255,255,255,.6)` + `box-shadow: 0 0 18px rgba(255,255,255,.18)`.
- No longer uses `.btn-primary`; keeps `aria-expanded`, labels unchanged.

## Risks / Trade-offs

- A translucent launcher is less prominent than the orange pill → acceptable; the brief is minimalism, and the hover glow + icon keep it discoverable.
- `backdrop-filter` unsupported → falls back to the semi-opaque fill, still readable.
