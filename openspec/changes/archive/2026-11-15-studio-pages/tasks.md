# Tasks

**How to verify:**
- **Frontend:** run `docker compose build web` and `docker compose up -d web`. Vitest runs in a throwaway `node:22-alpine` container.
- **Browser checks** use Playwright at 1280px and 360px against http://localhost:8080/prj1/.
- **No file by Tùng is edited.** Check with `git diff --stat`: only `src/router/index.js` is modified, the rest are new files, plus the docs.

## 1. Studio details

- [x] 1.1 Create `src/data/studio.js` with `STUDIO` (sample details: description, phone, email `…@….example`, Zalo, address, hours; the team's three real names with sample roles; the 5 process steps marked sample) and the helpers `telHref`, `mailHref`, `zaloHref` and `mapHref`.

  Verify with `src/data/studio.test.js`:
  - every helper returns `null` for a sample value;
  - a confirmed phone `0912 345 678` gives `tel:0912345678` and `https://zalo.me/0912345678`;
  - a confirmed address gives a Google Maps search URL with the address encoded;
  - a confirmed email gives `mailto:`.

## 2. Pages

- [x] 2.1 Create `src/views/ContactView.vue` and add the route `/lien-he`:
  - form, `#zalo`, `#ban-do`, the estimate and quiz links;
  - sample marks;
  - `scroll-margin-top` plus scroll-on-hash (on mount and on hash change);
  - the page title.

  Verify in the browser:
  - "Liên hệ" in the header opens it, highlighted as the current page;
  - sending the form stores a lead with `ngu_canh.trang = '/lien-he'` and no `du_an`. Use an `@example.com` email, then delete the lead;
  - sample values carry "Thông tin mẫu", and there is no `tel:`, `mailto:`, `zalo.me` or maps link on the page;
  - the footer "Nhắn Zalo" and "Địa chỉ và bản đồ" open the page with that section's heading fully below the header, at 360px and 1280px, also when already on `/lien-he`;
  - no sideways scroll at 360px;
  - the page title is right.
- [x] 2.2 Create `src/views/AboutView.vue` and add the route `/ve-chung-toi`:
  - intro, figures, team, steps, closing links;
  - sample marks;
  - the page title.

  Verify in the browser:
  - "Về chúng tôi" in the header opens it, highlighted;
  - the project count equals the number of cards on `/du-an`;
  - the three names are shown, and the roles carry the sample mark;
  - "Xem dự án" and "Liên hệ" go to their pages;
  - the heading is below the header and there is no sideways scroll at 360px and 1280px.

## 3. Docs

- [x] 3.1 Update `TONG-QUAN-DU-AN.md`:
  - roadmap 0.3 ✓ and 2.3 ✓;
  - UC11 (the contact page);
  - known issue 3: only `/dich-vu` and the `SpaceCard` link remain dead, with `/dich-vu` left to Tùng;
  - a short "Thông tin studio" note: edit `src/data/studio.js`, set `mau: false`, and update the "Quy trình" knowledge entry to match.

  Verify that vitest passes and the backend suite is unaffected (no backend change, so a run of `tests/test_leads.py` is enough).
