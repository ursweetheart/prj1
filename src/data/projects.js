/* ═══════════════════════════════════════════════════════════════════════
 * Danh sách dự án: lưới "Dự án" ở trang chủ và trang dự án /du-an/<slug>.
 *
 * TẠM THỜI: 5 dự án mẫu dùng ảnh đã thêm từ Behance. Khi có dữ liệu thật,
 * sửa trực tiếp file này. Mỗi dự án:
 *   - slug    : mã không dấu, là đường dẫn trang dự án (/du-an/<slug>)
 *   - name    : tên dự án hiển thị
 *   - loai    : chung-cu | nha-pho | villa (Nhà ở) · lounge | fnb | showroom | van-phong (Thương mại)
 *   - year    : năm hoàn thành
 *   - cover   : ảnh đại diện, đặt trong src/assets/projects/ rồi import ở dưới
 * Tuỳ chọn:
 *   - brief   : đoạn mô tả ngắn, hiện dưới tên dự án (bỏ trống thì không hiện gì)
 * Ảnh trong trang dự án: thả ảnh vào thư mục src/assets/projects/<slug>/
 *   (ví dụ src/assets/projects/du-an-mau-01/), sắp theo tên file: 01-…, 02-…
 *   Thư mục trống thì trang dự án chỉ hiện ảnh đại diện.
 * Thứ tự trong mảng là thứ tự hiển thị và thứ tự "Dự án trước / tiếp".
 * ═══════════════════════════════════════════════════════════════════ */
import cover01 from '@/assets/projects/du-an-mau-01.jpg'
import cover02 from '@/assets/projects/du-an-mau-02.jpg'
import cover03 from '@/assets/projects/du-an-mau-03.jpg'
import cover04 from '@/assets/projects/du-an-mau-04.jpg'
import cover05 from '@/assets/projects/du-an-mau-05.jpg'
import SIZES from 'virtual:project-image-sizes'

export const LOAI_NAME = {
  'chung-cu': 'Chung cư', 'nha-pho': 'Nhà phố', villa: 'Villa',
  lounge: 'Lounge', fnb: 'F&B', showroom: 'Showroom', 'van-phong': 'Văn phòng'
}

export const PROJECT_FILTERS = [
  { id: 'all', label: 'Tất cả' },
  { id: 'nha-o', label: 'Nhà ở', loai: ['chung-cu', 'nha-pho', 'villa'] },
  { id: 'thuong-mai', label: 'Thương mại', loai: ['lounge', 'fnb', 'showroom', 'van-phong'] }
]

// Kích thước thật của ảnh, đọc lúc build bởi vite-plugins/projectImageSizes.js
const DEFAULT_SIZE = [4, 3]

// Ảnh trong thư mục src/assets/projects/<slug>/ → { <slug>: [{ src, w, h }, …] }, theo tên file
const files = import.meta.glob('../assets/projects/*/*.{jpg,jpeg,png,webp,avif,JPG,JPEG,PNG,WEBP,AVIF}',
  { eager: true, import: 'default' })
const FOLDER_IMAGES = {}
Object.keys(files)
  .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
  .forEach(path => {
    const [slug, file] = path.split('/').slice(-2)
    const [w, h] = SIZES[slug + '/' + file] || DEFAULT_SIZE
    ;(FOLDER_IMAGES[slug] ||= []).push({ src: files[path], w, h })
  })

const PROJECTS = [
  { slug: 'du-an-mau-01', name: 'Dự án mẫu 01', loai: 'chung-cu', year: 2025, cover: cover01 },
  { slug: 'du-an-mau-02', name: 'Dự án mẫu 02', loai: 'villa',    year: 2025, cover: cover02 },
  { slug: 'du-an-mau-03', name: 'Dự án mẫu 03', loai: 'lounge',   year: 2024, cover: cover03 },
  { slug: 'du-an-mau-04', name: 'Dự án mẫu 04', loai: 'nha-pho',  year: 2024, cover: cover04 },
  { slug: 'du-an-mau-05', name: 'Dự án mẫu 05', loai: 'fnb',      year: 2023, cover: cover05 }
]

// Thư mục ảnh trống: trang dự án dùng ảnh đại diện (<slug>.jpg ở gốc src/assets/projects)
const coverImage = p => {
  const [w, h] = SIZES[p.slug + '.jpg'] || DEFAULT_SIZE
  return { src: p.cover, w, h }
}

export const PROJECTS_LIST = PROJECTS.map(p => ({
  ...p,
  images: FOLDER_IMAGES[p.slug] || [coverImage(p)]
}))

export const projectBySlug = slug => PROJECTS_LIST.find(p => p.slug === slug) || null
