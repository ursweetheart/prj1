## 1. Fix the overlap

- [x] 1.1 Diagnose: the `.nav-in` `1fr auto 1fr` grid with `.nav-center` hidden pushed `.nav-right` into the centre column while the brand kept its 72px / 36px desktop size
- [x] 1.2 Make the header mobile-first so brand and items cannot overlap; desktop bar uses `grid-template-columns: minmax(max-content, 1fr) auto minmax(max-content, 1fr)` from 1024px; large sizes from 1280px

## 2. Stacked header without a burger

- [x] 2.1 `src/components/SiteNav.vue`: remove the burger button, the `.nav-sheet` drawer and the `open` state
- [x] 2.2 `src/assets/app.css`: under 1024px `.nav-in` is a centred flex column (brand → main links → account + "Vi | En"), rows wrap and stay centred; remove the `.nav-burger` / `.nav-sheet` rules
- [x] 2.3 Breakpoints: 600px widens spacing and link size; 1024px switches to the one-row bar; 1280px restores the large desktop sizes

## 3. Brand

- [x] 3.1 Fluid brand on small screens: wordmark `clamp(28px, 9vw, 48px)`, mark `clamp(36px, 11.5vw, 62px)`
- [x] 3.2 Crop the transparent padding of `public/img/logo_xoa_nen.png` into `public/img/logo_mark.png` (230×258); keep the original file
- [x] 3.3 `src/components/BrandMark.vue`: use `img/logo_mark.png`; desktop mark heights 34px (1024px) and 46px (1280px)

## 4. Hover and legibility

- [x] 4.1 Lift + brighten on hover and `:focus-visible` for the brand, main links, account links/buttons and language buttons: `translateY(-3px)` (brand `-4px`), white, soft glow; 0.45s `cubic-bezier(0.22, 1, 0.36, 1)`; the active link keeps red with a red glow
- [x] 4.2 Stronger top gradient (`.72 → .45 → 0`), dark `text-shadow` on `.nav-in` and `drop-shadow` on the brand; hover glow layered on top of the dark shadow

## 5. Verification

- [x] 5.1 Measure the header boxes in the browser at 320, 360, 390, 414, 600, 768, 900, 1023, 1024, 1100, 1280 and 1440px: no overlap, document never wider than the viewport
- [x] 5.2 Visual check at 360, 414, 768 and ~1280px; hovering "Về chúng tôi" computes `translateY(-3px)`, white, glow
- [x] 5.3 `vite build` succeeds (built into a scratch directory so the tracked `dist/` is untouched)
- [ ] 5.4 Check the signed-in header (editor / sales: "Duyệt", "Khách hàng", "Đăng xuất") at 360px and 1024px for overlap
- [ ] 5.5 Check on a real phone (touch): the hover state must not stay stuck after a tap
