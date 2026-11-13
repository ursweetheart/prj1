## Why

Prototype hiện tại dùng Vue 3 qua CDN (`unpkg`) và inline `<script>` — phù hợp để dựng nhanh nhưng không mở rộng được: không có hot-reload, không có Single-File Component (SFC), không quản lý dependency, và không build được production bundle. Đồng thời, nội dung text hiện đang hardcode tiếng Việt mô tả thật của D3 Studio — cần chuyển sang **lorem ipsum** (đoạn giả) để prototype tập trung vào layout/UX mà không bị nhầm là nội dung cuối cùng.

Thiết kế (layout, màu sắc, typography, bộ lọc, mosaic grid…) phải **khớp hoàn toàn** với câu trả lời Google Form đã lưu trong file Excel (`Website D3 Studio (Câu trả lời).xlsx`), cụ thể:
- Câu 18: nền tối gần đen
- Câu 19: màu nhấn nâu gỗ / terracotta
- Câu 20: sans-serif
- Câu 21: đoạn văn dài xen giữa ảnh (kiểu tạp chí)
- Câu 26: vài công trình nổi bật rồi mới đến lưới đầy đủ
- Câu 27: mosaic, ảnh to nhỏ xen kẽ
- Câu 30: không hiệu ứng chuyển động — vào là hiện luôn
- Câu 31: bộ lọc ở cột dọc bên trái

## What Changes

- **Migrate sang Vue 3 project (Vite)**: Chuyển từ CDN + inline script sang project Vue 3 + Vite với SFC, dev server, HMR.
- **Giữ nguyên thiết kế hiện tại**: Toàn bộ CSS design tokens, layout, component logic (data.js, components.js) được port sang SFC — không thay đổi giao diện.
- **Thay text → lorem ipsum**: Mọi đoạn text mô tả, heading, lead paragraph, note, brief, eyebrow… trong `index.html` và `data.js` chuyển thành lorem ipsum. Giữ nguyên cấu trúc (tag, class, độ dài tương đương).
- **Giữ nguyên tài nguyên từ `D:\prj1`**: Ảnh (`img/`), logo, và dữ liệu facet/project structure được giữ lại, chỉ thay nội dung text.

## Capabilities

### New Capabilities
- `vue-vite-setup`: Khởi tạo project Vue 3 + Vite, cấu hình dev server, chuyển đổi HTML pages thành Vue SFC components, thiết lập router cho multi-page.
- `lorem-content`: Thay thế toàn bộ nội dung text (headings, descriptions, notes, briefs, labels UI) bằng lorem ipsum, giữ nguyên cấu trúc HTML và độ dài tương đương.

### Modified Capabilities
_(Không có capability nào hiện hữu trong openspec/specs/ để modify)_

## Impact

- **Cấu trúc thư mục**: Thêm `package.json`, `vite.config.js`, `src/` chứa SFC. Các file gốc (`index.html`, `cong-trinh.html`, `css/app.css`, `js/data.js`, `js/components.js`) được port sang cấu trúc Vue mới.
- **Dependency**: Thêm `vue@3`, `vite`, `@vitejs/plugin-vue`, `vue-router@4`.
- **Dev workflow**: Chạy `npm run dev` thay vì mở file trực tiếp.
- **Ảnh và assets**: Thư mục `img/` được copy sang `public/img/` hoặc `src/assets/` — không thay đổi nội dung ảnh.
- **Không breaking change về mặt thiết kế**: Layout, màu sắc, typography, bộ lọc, mosaic grid giữ nguyên 100% theo file Excel.
