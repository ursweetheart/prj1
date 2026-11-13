## Context

`HomeView.vue` renders `.hero > .media > img` with one image from `public/img`. The fixed site header sits on top of the hero. No backend is required for the home page.

## Decisions

### Image source: `src/assets/hero/` + `import.meta.glob`
A browser cannot list a folder, so the images are collected at build time with `import.meta.glob('../assets/hero/*.{jpg,jpeg,png,webp,avif}', { eager: true, import: 'default' })` and sorted by file name. Dropping a file into the folder is enough; in dev Vite picks it up without a restart. Alternative (`public/` + a hand-written list) rejected: every new photo would need a code edit.

### Crossfade with layered slides
All slides are stacked absolutely. The active slide is on top (`z-index: 2`) and fades from 0 to 1 over 1.2s; the slide being left stays fully visible underneath (`z-index: 1`) until the fade ends, so the fade never dips to the dark background.

### Click the left / right half
Two transparent `<button>`s cover the left and right halves of the hero ("Ảnh trước" / "Ảnh sau"). Clicking or tapping one goes to the previous / next photo with the same crossfade. The cursor stays the normal arrow; a thin chevron fades in at that edge on hover (shown faintly on touch screens, which have no hover). Being real buttons they are keyboard-focusable and announced by screen readers, and they do not interfere with vertical scrolling on phones.

An earlier iteration used mouse drag / swipe with the opacity following the pointer; replaced by click zones at the user's request (2026-11-01).

When a project page exists, clicking a photo to open it will need its own target (e.g. a caption link), since both halves are taken by navigation.

### Timer
One `setTimeout` of 13s, restarted on every slide change (automatic, click zone, dot, key). Hover does not stop it. The active dot's progress bar is a 13s CSS animation restarted by re-keying the element.

### Loading
A slide gets its `src` only once it is the current, next or previous slide; after that it stays loaded. The first slide is `loading="eager"` with `fetchpriority="high"`.

### Reduced motion
With `prefers-reduced-motion: reduce` there is no timer, no progress animation and no fade transition.

## Risks / Trade-offs

- Large photos (the current one is 1.1 MB) cost bandwidth; mitigated by loading only neighbours. Compressing photos before adding them is recommended.
- Keyboard arrows only act when focus is inside the hero (a click zone or dot), to avoid clashing with form fields and the chat widget.
