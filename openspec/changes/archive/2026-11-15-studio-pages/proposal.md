# Proposal

## Why

The header and footer on every page link to "Về chúng tôi" (`/ve-chung-toi`) and "Liên hệ" (`/lien-he`, `/lien-he#zalo`, `/lien-he#ban-do`). The home CTA also links to `/lien-he`. None of these routes exist, so the first thing a visitor or a grader clicks leads to an empty page.

The contact form (`ContactForm.vue`, `POST /leads`) is already built, and its spec already expects to be embedded on `/lien-he`. Only the page around it is missing.

This is roadmap item 0.3, and it finishes 2.3.

## What Changes

- **`/lien-he` (Liên hệ):**
  - the existing `<ContactForm />`, with no project; leads record the page `/lien-he`;
  - the studio's phone, email and Zalo, in a block anchored `#zalo`;
  - address, opening hours and an "Mở bản đồ" link, in a block anchored `#ban-do`;
  - links to `/uoc-tinh` and `/trac-nghiem` for visitors not ready to call.
- **`/ve-chung-toi` (Về chúng tôi):**
  - who D3 Studio is: architecture, interiors and 3D visualisation in Hà Nội;
  - the team: Phạm Việt Tùng, Trần Xuân Bằng, Trần Xuân Tuấn;
  - how a project runs, in short steps;
  - a few numbers taken from the site's own data (the number of projects on `/du-an`);
  - links to `/du-an` and `/lien-he`.
- **Studio details in one place:** a new `src/data/studio.js` holds them. Each value that is still a sample is flagged and shown with a "Thông tin mẫu" mark.
  - A sample phone, email or Zalo is shown as text, not as a working `tel:` / `mailto:` / Zalo link, so a visitor never calls or messages a stranger's number.
  - A sample address gets no map link.
  - Replacing a value and removing its flag makes it live.
- **Hash links land below the fixed header:** `/lien-he#zalo` and `/lien-he#ban-do` from the footer, on a phone and on a desktop.
- **Page titles:** both pages set `document.title`.

**Decisions taken with the user:**
- **The studio details are sample values, clearly marked.** The real address, phone, Zalo, hours and bios are not available yet.
- **`/dich-vu` ("Dịch vụ và quy trình" in the footer) is not part of this change, and none of Tùng's files are edited.** `App.vue` already maps `/dich-vu`, so that page is left to Tùng. This change adds new files and only two route lines in `src/router/index.js`. `App.vue`, `SiteFoot.vue`, `SiteNav.vue`, `HomeView.vue`, `ProjectView.vue`, `src/data/projects.js` and `app.css` are not modified.

## Capabilities

### New Capabilities
- `studio-pages`: the public "Về chúng tôi" and "Liên hệ" pages, the studio details they show, and how sample details are marked and kept from acting as real contact links.

### Modified Capabilities
None. `leads/contact-form` already requires that the form, embedded on `/lien-he`, sends the page `/lien-he`. This change embeds it without changing the form. The header and footer specs already list the links.

## Impact

- **New files:**
  - `src/views/ContactView.vue`;
  - `src/views/AboutView.vue`;
  - `src/data/studio.js`;
  - `src/data/studio.test.js` (vitest: the link helpers never produce a link from a sample value).
- **Edited:** `src/router/index.js`, two routes. The route names `lien-he` and `ve-chung-toi` match the nav keys `App.vue` already uses.
- **No backend change, no schema change.** Leads go through the existing `POST /leads`.
- **Docs:** `TONG-QUAN-DU-AN.md` (roadmap 0.3 and 2.3, known issue 3 "link chết", UC11, and where to put the real details).
- **Out of scope:**
  - `/dich-vu`;
  - an embedded Google map (a link only, so no third-party frame and no consent question);
  - the "Vi | En" switch (no English content exists on the site yet);
  - team photos;
  - real studio details.
