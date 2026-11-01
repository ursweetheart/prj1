/* ═══════════════════════════════════════════════════════════════════════
 * Danh sách dự án ở trang chủ (lưới "Dự án").
 *
 * TẠM THỜI: 5 dự án mẫu dùng ảnh đã thêm từ Behance. Khi có dữ liệu thật,
 * sửa trực tiếp file này:
 *   - name  : tên dự án hiển thị
 *   - slug  : mã không dấu, dùng cho trang dự án sau này
 *   - loai  : chung-cu | nha-pho | villa (Nhà ở) · lounge | fnb | showroom | van-phong (Thương mại)
 *   - year  : năm hoàn thành
 *   - cover : ảnh đại diện, đặt trong src/assets/projects/ rồi import ở dưới
 * Thứ tự trong mảng là thứ tự hiển thị.
 * ═══════════════════════════════════════════════════════════════════ */
import cover01 from '@/assets/projects/du-an-mau-01.jpg'
import cover02 from '@/assets/projects/du-an-mau-02.jpg'
import cover03 from '@/assets/projects/du-an-mau-03.jpg'
import cover04 from '@/assets/projects/du-an-mau-04.jpg'
import cover05 from '@/assets/projects/du-an-mau-05.jpg'

export const LOAI_NAME = {
  'chung-cu': 'Chung cư', 'nha-pho': 'Nhà phố', villa: 'Villa',
  lounge: 'Lounge', fnb: 'F&B', showroom: 'Showroom', 'van-phong': 'Văn phòng'
}

export const HOME_FILTERS = [
  { id: 'all', label: 'Tất cả' },
  { id: 'nha-o', label: 'Nhà ở', loai: ['chung-cu', 'nha-pho', 'villa'] },
  { id: 'thuong-mai', label: 'Thương mại', loai: ['lounge', 'fnb', 'showroom', 'van-phong'] }
]

export const HOME_PROJECTS = [
  { slug: 'du-an-mau-01', name: 'Dự án mẫu 01', loai: 'chung-cu', year: 2025, cover: cover01 },
  { slug: 'du-an-mau-02', name: 'Dự án mẫu 02', loai: 'villa',    year: 2025, cover: cover02 },
  { slug: 'du-an-mau-03', name: 'Dự án mẫu 03', loai: 'lounge',   year: 2024, cover: cover03 },
  { slug: 'du-an-mau-04', name: 'Dự án mẫu 04', loai: 'nha-pho',  year: 2024, cover: cover04 },
  { slug: 'du-an-mau-05', name: 'Dự án mẫu 05', loai: 'fnb',      year: 2023, cover: cover05 }
]
