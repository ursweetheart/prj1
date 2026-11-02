## 1. Shared hover

- [x] 1.1 `src/assets/app.css`: `.glow-hover` utility copying the top-bar hover (lift 3px, white, text glow, 0.45s curve); reduced motion = glow without lift

## 2. Home CTA

- [x] 2.1 `src/views/HomeView.vue`: replace the `.panel` CTA with the open block (eyebrow "Liên hệ", heading, sentence, two arrow links with `.glow-hover`)
- [x] 2.2 `src/assets/app.css`: `.cta` styles — 1120px container aligned with the grid, hairline rule, light heading, two columns from 900px, stacked below, arrow nudge on hover

## 3. Assistant launcher

- [x] 3.1 `src/components/ChatWidget.vue`: launcher without `.btn-primary`; chat icon + label; `.glow-hover`
- [x] 3.2 Scoped style: translucent dark pill, hairline border, blur; hover/focus border + soft box glow

## 4. Verification

- [x] 4.1 Browser check: CTA at 1280px and 390px (alignment with grid, no horizontal scroll), launcher readable over the hero and over the dark page, hover lift/glow on both, chat still opens/closes, no console errors
- [x] 4.2 `vite build` into a scratch directory succeeds

## 5. Footer brand (user request)

- [x] 5.1 Footer logo mark and "D3 STUDIO" on one row like the header: `.foot a.brand { display: inline-flex }` (the generic `.foot a { display: block }` was stacking them)
