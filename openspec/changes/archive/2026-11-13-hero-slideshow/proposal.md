## Why

The first screen of the home page shows one fixed photo (`public/img/indochine-apartment-hero.jpg`). The studio wants to show several of its works there and to swap the photos without touching code.

## What Changes

- New image folder `src/assets/hero/`: every image in it is shown on the hero, ordered by file name. The current hero photo is copied in as `01-indochine-apartment.jpg`.
- The hero becomes a slideshow: crossfade to the next photo every 13 seconds; hovering does not pause it.
- Visitors click (tap) the left half of the hero to go to the previous photo and the right half to go to the next one, with the same crossfade; a faint arrow appears at the edge on hover.
- Position dots at the bottom; the active dot fills like a 13-second progress bar; clicking a dot jumps to that photo.
- Arrow keys ← → change photo when the hero has focus.
- Only the current, next and previous photos are loaded.
- `prefers-reduced-motion`: no auto-advance and no fade; click zones, dots and keys still work.
- With a single image the hero looks like today (no dots, no click zones).

## Non-goals

- Clicking a photo to open its project page: there is no project page yet; to be added in a later change.
- Captions or per-image metadata.

## Capabilities

### New Capabilities
- `home-hero-slideshow`: the rotating photo hero on the home page.

## Impact

- `src/views/HomeView.vue` (hero markup), new `src/components/HeroSlideshow.vue`, `src/assets/app.css` (hero rules), new folder `src/assets/hero/`.
