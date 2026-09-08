## 1. Project Scaffolding

- [x] 1.1 Khởi tạo Vue 3 + Vite project: tạo `package.json`, `vite.config.js`, `index.html` (entry point Vite) tại root `d:\prj1\prototype\`
- [x] 1.2 Cài dependencies: `vue@3`, `vue-router@4`, `@vitejs/plugin-vue`, `vite`
- [x] 1.3 Tạo cấu trúc thư mục `src/` với các folder: `components/`, `composables/`, `data/`, `views/`, `router/`, `assets/`
- [x] 1.4 Copy thư mục `img/` sang `public/img/`

## 2. CSS & Entry Point

- [x] 2.1 Port `css/app.css` sang `src/assets/app.css` (giữ nguyên nội dung)
- [x] 2.2 Tạo `src/main.js`: import Vue, import router, import CSS, mount app
- [x] 2.3 Tạo `src/App.vue`: layout shell với `<router-view />` 

## 3. Data Module

- [x] 3.1 Port `js/data.js` sang `src/data/index.js` dưới dạng ES module (named exports thay vì `window.D3`)
- [x] 3.2 Thay text content trong data (project `name`, `brief`, `note`, space `space` name) bằng lorem ipsum — giữ nguyên structure, IDs, facet values

## 4. Composables

- [x] 4.1 Tạo `src/composables/useMoodboard.js`: extract moodboard store logic (has, toggle, count, localStorage)
- [x] 4.2 Tạo `src/composables/useBrowse.js`: extract useBrowse composable (selected, results, counts, activeChips, toggle, clear, clearAll + hash sync)

## 5. Components (SFC)

- [x] 5.1 Tạo `src/components/BrandMark.vue`: SVG brand mark
- [x] 5.2 Tạo `src/components/SiteNav.vue`: thanh điều hướng, dùng `<router-link>` thay `<a href>`
- [x] 5.3 Tạo `src/components/SiteFoot.vue`: footer, dùng `<router-link>`
- [x] 5.4 Tạo `src/components/SpaceCard.vue`: thẻ không gian với moodboard toggle
- [x] 5.5 Tạo `src/components/FacetPanel.vue`: bộ lọc cột dọc
- [x] 5.6 Tạo `src/components/Lightbox.vue`: dialog phóng to ảnh
- [x] 5.7 Tạo `src/components/BeforeAfter.vue`: so sánh concept/thực tế
- [x] 5.8 Tạo `src/components/HotspotImage.vue`: ảnh có điểm nóng
- [x] 5.9 Tạo `src/components/PaletteRow.vue`: dải màu chủ đạo

## 6. Views & Router

- [x] 6.1 Tạo `src/views/HomeView.vue`: port từ `index.html`, thay text → lorem ipsum (hero, magazine section, featured spaces, CTA panel)
- [x] 6.2 Tạo `src/views/CongTrinhView.vue`: port từ `cong-trinh.html`, thay text → lorem ipsum (page header, empty state text)
- [x] 6.3 Tạo `src/router/index.js`: định nghĩa routes (`/` → HomeView, `/cong-trinh` → CongTrinhView)

## 7. Lorem Ipsum Content

- [x] 7.1 Thay text nội dung trong `HomeView.vue`: hero heading, hero lead, eyebrows, magazine body, CTA heading + description
- [x] 7.2 Thay text nội dung trong `CongTrinhView.vue`: page heading, lead paragraph, empty state text
- [x] 7.3 Thay text nội dung trong `SiteFoot.vue`: footer description paragraph
- [x] 7.4 Thay text trong `SERVICES` và `PROCESS` data (name, desc) bằng lorem ipsum

## 8. Verification

- [x] 8.1 Chạy `npm run dev` (hoặc `npm run build`), verify trang chủ render đúng layout
- [x] 8.2 Verify trang Công trình: bộ lọc hoạt động
- [x] 8.3 Verify navigation giữa hai trang qua SiteNav không reload trang
- [x] 8.4 Verify tất cả ảnh load đúng (không 404)
- [x] 8.5 Verify text content là lorem ipsum, không còn nội dung tiếng Việt mô tả thật
