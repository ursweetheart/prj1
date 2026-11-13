## 1. Image folder

- [x] 1.1 Create `src/assets/hero/` and copy `public/img/indochine-apartment-hero.jpg` into it as `01-indochine-apartment.jpg` (keep the original)
- [x] 1.2 Add a short `README.md` in the folder: supported formats, ordering by file name, recommended size

## 2. Slideshow component

- [x] 2.1 `src/components/HeroSlideshow.vue`: collect images with `import.meta.glob`, sort by name, layered crossfade, 13s timer
- [x] 2.2 Pointer drag (6px start, 15% commit, opacity follows pointer, `touch-action: pan-y`)
- [x] 2.3 Position dots with a 13s progress fill; click to jump
- [x] 2.4 ← → keys when the hero has focus; load only current/next/previous; reduced motion; single-image fallback
- [x] 2.5 Hero slideshow styles in `src/assets/app.css`

## 3. Wire up

- [x] 3.1 `src/views/HomeView.vue`: replace the single hero image with `<HeroSlideshow />`

## 4. Verification

- [x] 4.1 Browser check: auto-advance, drag commit/cancel, dots, keys, no console errors
- [x] 4.2 `vite build` into a scratch directory succeeds

## 5. Click zones instead of drag (user request)

- [x] 5.1 Remove pointer drag (handlers, drag opacity, `touch-action`, grab cursors)
- [x] 5.2 Two transparent buttons over the left / right halves ("Ảnh trước" / "Ảnh sau") with the normal cursor and a chevron that fades in on hover; same crossfade
- [x] 5.3 Browser check: left/right click incl. wrap-around, dots still clickable above the zones, header links still clickable, no console errors; build succeeds
