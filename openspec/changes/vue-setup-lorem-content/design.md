## Context

Prototype website D3 Studio hiện tại chạy bằng Vue 3 CDN (`unpkg`) + inline scripts. Cấu trúc:
- `index.html`, `cong-trinh.html` — hai trang HTML tĩnh dùng Vue template syntax
- `js/data.js` — dữ liệu FACETS, PROJECTS, SPACES, SERVICES, PROCESS
- `js/components.js` — Vue components (SiteNav, SiteFoot, SpaceCard, FacetPanel, Lightbox, BeforeAfter, HotspotImage, PaletteRow) + composable `useBrowse()`
- `css/app.css` — design system tokens + toàn bộ styling (463 dòng)
- `img/` — 10 file ảnh (logo.jpg, pic1-9.jpg)

Thiết kế tuân theo câu trả lời Google Form (Excel): nền tối, accent terracotta, sans-serif, mosaic grid, bộ lọc cột trái, không animation.

## Goals / Non-Goals

**Goals:**
- Chuyển sang Vue 3 + Vite project với SFC, HMR, dev server
- Port nguyên vẹn toàn bộ components, logic lọc, design tokens, layout
- Thay text content → lorem ipsum (giữ cấu trúc tag/class/độ dài)
- Sử dụng `vue-router` cho navigation giữa các trang
- Giữ tài nguyên ảnh từ `D:\prj1\prototype\img\`

**Non-Goals:**
- Không thay đổi thiết kế (layout, color, typography, spacing)
- Không thêm feature mới (chỉ migrate + thay text)
- Không build SSR/SSG — chỉ cần SPA dev mode
- Không thay đổi cấu trúc dữ liệu (FACETS, PROJECTS, SPACES)

## Decisions

### 1. Vite + `@vitejs/plugin-vue` thay vì Vue CLI hoặc Nuxt

**Chọn**: Vite
**Lý do**: Vite nhẹ, nhanh, là tool chính thức được Vue team recommend. Vue CLI đã deprecated. Nuxt quá nặng cho prototype không cần SSR.

### 2. Cấu trúc thư mục

```
d:\prj1\prototype\
├── public/
│   └── img/           ← copy từ img/ hiện tại
├── src/
│   ├── assets/
│   │   └── app.css    ← port từ css/app.css
│   ├── components/
│   │   ├── BrandMark.vue
│   │   ├── SiteNav.vue
│   │   ├── SiteFoot.vue
│   │   ├── SpaceCard.vue
│   │   ├── FacetPanel.vue
│   │   ├── Lightbox.vue
│   │   ├── BeforeAfter.vue
│   │   ├── HotspotImage.vue
│   │   └── PaletteRow.vue
│   ├── composables/
│   │   ├── useBrowse.js
│   │   └── useMoodboard.js
│   ├── data/
│   │   └── index.js   ← port từ js/data.js, text → lorem ipsum
│   ├── views/
│   │   ├── HomeView.vue     ← port từ index.html
│   │   └── CongTrinhView.vue ← port từ cong-trinh.html
│   ├── router/
│   │   └── index.js
│   ├── App.vue
│   └── main.js
├── index.html
├── vite.config.js
└── package.json
```

### 3. Ảnh đặt trong `public/img/` (không import)

**Lý do**: Ảnh nặng, đường dẫn `img/pic1.jpg` giữ giống gốc, không cần Vite xử lý hash. Copy nguyên thư mục `img/` sang `public/img/`.

### 4. CSS giữ nguyên file, import global

**Lý do**: `app.css` đã là design system hoàn chỉnh (463 dòng) với tokens + utilities. Import vào `main.js` là đủ. Không cần tách scoped CSS vào từng SFC vì prototype chung quy đều dùng chung class.

### 5. Lorem ipsum strategy

- Headings (`h-hero`, `h-1`, `h-2`, `h-3`): thay bằng lorem ipsum ngắn (~4-8 từ)
- Lead paragraphs (`.lead`): lorem ipsum ~2-3 câu
- Body (`.body`): lorem ipsum ~3-5 câu
- Eyebrow (`.eyebrow`): lorem ipsum 2-3 từ
- Data fields (`brief`, `note`, `space` name): lorem ipsum tương đương độ dài
- **KHÔNG thay**: tên facet/filter (Loại công trình, Phong cách…), label UI (Bộ lọc, Bỏ hết…), navigation items

## Risks / Trade-offs

- **Risk**: Port component logic có thể break behavior lọc → **Mitigation**: Test manual từng bộ lọc sau khi port
- **Risk**: Đường dẫn ảnh bể khi chuyển public/ → **Mitigation**: Dùng `/img/` (absolute from public root)
- **Trade-off**: Giữ CSS global thay vì scoped → Chấp nhận vì prototype, không cần isolation
- **Trade-off**: SPA thay vì multi-page → URL routing qua vue-router thay vì file-based
