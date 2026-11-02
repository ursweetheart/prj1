/* Chia ảnh dự án thành các hàng cho trang dự án (kiểu elemental.com.vn):
 *   - ảnh ngang (rộng / cao ≥ 1.25): một mình một hàng, trọn bề ngang;
 *   - ảnh dọc / vuông liền nhau: ghép đôi trên một hàng (CSS cho cao bằng nhau);
 *   - ảnh dọc / vuông lẻ: một mình, `lone: true` (đặt giữa, thu nhỏ).
 * Giữ nguyên thứ tự ảnh. images: [{ src, w, h }] → [{ items, lone }] */
export const LANDSCAPE = 1.25

export function galleryRows(images) {
  const rows = []
  let waiting = null
  const flush = () => {
    if (waiting) rows.push({ items: [waiting], lone: true })
    waiting = null
  }
  for (const img of images) {
    if (img.w / img.h >= LANDSCAPE) {
      flush()
      rows.push({ items: [img], lone: false })
    } else if (waiting) {
      rows.push({ items: [waiting, img], lone: false })
      waiting = null
    } else {
      waiting = img
    }
  }
  flush()
  return rows
}
