# Design

## Context

- **Links that already point here:**
  - `SiteNav.vue`: "Về chúng tôi" `/ve-chung-toi`, "Liên hệ" `/lien-he`;
  - `SiteFoot.vue`: `/ve-chung-toi`, `/lien-he`, `/lien-he#zalo`, `/lien-he#ban-do`;
  - `HomeView.vue`: the CTA to `/lien-he`.
  
  `App.vue` already maps the paths `/ve-chung-toi` and `/lien-he` to the nav keys, so the active link highlights without any edit.
- **Ownership.** Those files, the home page, the project pages, `src/data/projects.js` and the gallery and hero components are Tùng's work. The user asked that Tùng's changes not be touched. The router is shared and has been edited by everyone; adding routes there is the only way to make the pages reachable.
- **The form.** `ContactForm.vue` takes the props `project`, `spaceId` and `title`. It sends `trang: route.path` itself, so on `/lien-he` the lead records `/lien-he`, as `leads/contact-form` already requires.
- **Scrolling.** The router's `scrollBehavior` scrolls a hash to `{ el, top: 110 }`. That clears the 1024px+ header, but not the ~205px stacked header on a phone. Pages place their content below the header with `.page-top` (224 / 232 / 128 px).
- **Process wording.** The assistant's sample knowledge base describes the process in 5 steps: tư vấn và khảo sát → ý tưởng mặt bằng → phối cảnh 3D → bản vẽ thi công → thi công và bàn giao. It is marked `[DỮ LIỆU MẪU]`, and the About page uses the same steps so the site and the assistant agree.
- **Project count.** `PROJECTS_LIST` from `src/data/projects.js` (the projects shown on `/du-an`) is only read, never changed.

## Goals / Non-Goals

**Goals:**
- No dead header, footer or CTA link to these two pages.
- One place to put the real details later.
- Sample details can never act as a real phone, email, Zalo or address.
- No edit to Tùng's files.

**Non-Goals:**
- `/dich-vu`;
- an embedded map;
- English content;
- team photos;
- a CMS for these texts.

## Decisions

### 1. `src/data/studio.js`: details with a sample flag
```js
export const STUDIO = {
  ten: 'D3 Studio',
  mo_ta: '…',                 // one paragraph, sample
  dien_thoai: { gia_tri: '0900 000 000', mau: true },
  email:      { gia_tri: 'lienhe@d3studio.example', mau: true },
  zalo:       { gia_tri: '0900 000 000', mau: true },   // the Zalo phone number
  dia_chi:    { gia_tri: '…, Hà Nội', mau: true },
  gio_lam:    { gia_tri: 'Thứ Hai – Thứ Bảy, 8:30 – 17:30', mau: true },
  doi_ngu: [{ ten: 'Phạm Việt Tùng', vai_tro: '…', mau_vai_tro: true }, …],
  quy_trinh: [{ buoc: 'Tư vấn và khảo sát', mo_ta: '…' }, …], quy_trinh_mau: true,
}
export const telHref = d => d.mau ? null : 'tel:' + d.gia_tri.replace(/[^\d+]/g, '')
export const mailHref = d => d.mau ? null : 'mailto:' + d.gia_tri
export const zaloHref = d => d.mau ? null : 'https://zalo.me/' + d.gia_tri.replace(/\D/g, '')
export const mapHref = d => d.mau ? null : 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(d.gia_tri)
```
- **Sample values are clearly fake.** Domains end in `.example`, a reserved TLD. The sample phone is `0900 000 000`. A helper that returns `null` makes the page render plain text.
- **Unit-tested:** every helper returns `null` while `mau` is true, and the right link when it is false.
- **Alternative:** read the details from the backend's knowledge base. That would make the pages depend on the API, and the site also runs on GitHub Pages without one. A plain module also works on Pages.

### 2. A small `SampleMark` inline element
A `<span class="mau">Thông tin mẫu</span>` sits next to each sample value. For screen readers it carries `aria-label="thông tin mẫu, chưa phải thông tin thật"`. It lives locally in each view (a few lines of scoped CSS), so no shared stylesheet is touched.

### 3. `ContactView.vue` (`/lien-he`)
- **Layout:** `main.wrap.wrap-wide.page-top`. Two columns from 900px, stacked below that:
  - **left:** the heading "Liên hệ", one line of intro, then `<ContactForm title="Gửi yêu cầu tư vấn" />`;
  - **right:**
    - `section#zalo`: "Gọi hoặc nhắn" with phone, Zalo and email;
    - `section#ban-do`: "Văn phòng" with address, hours and "Mở bản đồ";
    - "Chưa sẵn sàng gọi?": links to `/uoc-tinh` and `/trac-nghiem`.
- **Hash scrolling:**
  - `#zalo` and `#ban-do` get `scroll-margin-top` equal to the `.page-top` values.
  - The router only offsets by 110px, so on mount, when `route.hash` names one of them, the page calls `el.scrollIntoView({ block: 'start' })` after `nextTick`. That respects `scroll-margin-top`.
  - It also runs when the hash changes while the page stays open: the footer links work from the contact page itself.
- **Title:** `document.title = 'Liên hệ · D3 Studio'`.

### 4. `AboutView.vue` (`/ve-chung-toi`)
- **Sections:**
  1. an intro (heading "Về D3 Studio", the `mo_ta` paragraph);
  2. a figure row: `PROJECTS_LIST.length` "dự án đã thực hiện", the number of project types, and "Hà Nội";
  3. "Đội ngũ": three cards with name and role. The names are real (the team). The roles are sample and marked;
  4. "Cách chúng tôi làm việc": the 5 steps as an ordered list, marked sample as a whole;
  5. a closing row: "Xem dự án" → `/du-an`, "Liên hệ" → `/lien-he`.
- **Title:** `document.title = 'Về chúng tôi · D3 Studio'`.

### 5. Router
In `src/router/index.js`, two lazy routes: `{ path: '/ve-chung-toi', name: 've-chung-toi', … }` and `{ path: '/lien-he', name: 'lien-he', … }`. Nothing else in the router changes.

## Risks / Trade-offs

- **[Sample details look real enough to mislead]** → Values are obviously fake (`.example`, `0900 000 000`), each is marked, and none is a working link.
- **[Hash scroll fights the router's own scroll]** → The page scrolls after the router, at `nextTick` on mount. The browser check covers 360px and 1280px from the footer links.
- **[Process steps disagree with the assistant later]** → Both are marked sample. The doc tells whoever enters the real process to update both `studio.js` and the "Quy trình" knowledge entry.
- **[`/dich-vu` stays dead]** → Intentional, per the user. It is noted in the doc's known-issues list.

## Migration Plan

- Frontend only: run `docker compose build web`.
- **To go live:** edit `src/data/studio.js`, set each confirmed value and `mau: false`.
- **Rollback:** remove the two routes.
