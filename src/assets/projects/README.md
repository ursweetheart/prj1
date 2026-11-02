# Ảnh dự án

- Mỗi dự án một thư mục `<slug>/` (trùng `slug` trong `src/data/projects.js`).
- Ảnh sắp theo tên file: `01.jpg`, `02.jpg`, … Ảnh `01` là ảnh đại diện trên lưới dự án.
- Định dạng: `.jpg`, `.jpeg`, `.png`, `.webp`, `.avif`.
- Nén ảnh trước khi thêm: cạnh dài 1600px, chất lượng ~75 (khoảng 200–400 KB/ảnh), ví dụ:
  `magick in.jpg -resize "1600x1600>" -strip -interlace JPEG -quality 75 01.jpg`
