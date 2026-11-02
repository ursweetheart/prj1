/* ═══════════════════════════════════════════════════════════════════════
 * Danh sách dự án: lưới "Dự án" ở trang chủ, trang /du-an và trang dự án /du-an/<slug>.
 *
 * Mỗi dự án:
 *   - slug  : mã không dấu, là đường dẫn trang dự án (/du-an/<slug>)
 *             và tên thư mục ảnh src/assets/projects/<slug>/
 *   - name  : tên dự án hiển thị
 *   - loai  : Nhà ở: chung-cu | nha-pho | villa | phong (thiết kế phòng lẻ)
 *             Thương mại: lounge | fnb | khach-san | spa | showroom | van-phong
 * Tuỳ chọn:
 *   - year  : năm hoàn thành (bỏ trống thì không hiện)
 *   - brief : đoạn mô tả ngắn, hiện dưới tên dự án
 * Ảnh: thư mục src/assets/projects/<slug>/, sắp theo tên file (01.jpg, 02.jpg, …).
 *   Ảnh đầu tiên là ảnh đại diện trên lưới dự án.
 * Thứ tự trong mảng là thứ tự hiển thị và thứ tự "Dự án trước / tiếp".
 * ═══════════════════════════════════════════════════════════════════ */
import SIZES from 'virtual:project-image-sizes'

export const LOAI_NAME = {
  'chung-cu': 'Chung cư', 'nha-pho': 'Nhà phố', villa: 'Villa', phong: 'Thiết kế phòng',
  lounge: 'Lounge', fnb: 'F&B', 'khach-san': 'Khách sạn', spa: 'Spa & thẩm mỹ',
  showroom: 'Showroom', 'van-phong': 'Văn phòng'
}

export const PROJECT_FILTERS = [
  { id: 'all', label: 'Tất cả' },
  { id: 'nha-o', label: 'Nhà ở', loai: ['chung-cu', 'nha-pho', 'villa', 'phong'] },
  { id: 'thuong-mai', label: 'Thương mại', loai: ['lounge', 'fnb', 'khach-san', 'spa', 'showroom', 'van-phong'] }
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
  { slug: 'uri-lounge',                   loai: 'lounge',    name: 'URI Lounge' },
  { slug: 'indochine-chinoiserie-villa',  loai: 'villa',     name: 'Indochine – Chinoiserie Villa' },
  { slug: 'luxury-apartment',             loai: 'chung-cu',  name: 'Luxury Apartment' },
  { slug: 'zeus-lounge',                  loai: 'lounge',    name: 'Zeus Lounge' },
  { slug: 'wallnut-villa',                loai: 'villa',     name: 'Wallnut Villa' },
  { slug: 'hanjadin-apartment',           loai: 'chung-cu',  name: 'Hanjadin Apartment' },
  { slug: 'cosmos-lounge',                loai: 'lounge',    name: 'Cosmos Lounge' },
  { slug: 'lam-dong-villa',               loai: 'villa',     name: 'Lam Dong Villa' },
  { slug: 'modern-townhouse',             loai: 'nha-pho',   name: 'Modern Townhouse' },
  { slug: 'beaumont-lounge',              loai: 'lounge',    name: 'Beaumont Lounge' },
  { slug: 'modern-wabisabi-apartment',    loai: 'chung-cu',  name: 'Modern Wabi-sabi Apartment' },
  { slug: 'hd-villa',                     loai: 'villa',     name: 'HD Villa – Modern Dark Tone' },
  { slug: 'luxy-lounge',                  loai: 'lounge',    name: 'Luxy Lounge' },
  { slug: 'indochine-apartment',          loai: 'chung-cu',  name: 'Indochine Apartment I' },
  { slug: 'contemporary-villa',           loai: 'villa',     name: 'Contemporary Villa' },
  { slug: 'korean-bbq-restaurant',        loai: 'fnb',       name: 'Korean BBQ Restaurant' },
  { slug: 'coral-dot',                    loai: 'chung-cu',  name: 'Coral Dot' },
  { slug: 'modern-classic-villa',         loai: 'villa',     name: 'Modern Classic Villa' },
  { slug: 'coffee-shop',                  loai: 'fnb',       name: 'Coffee Shop' },
  { slug: 'vinhomes-gardenia',            loai: 'chung-cu',  name: 'Mrs. Yen – Vinhomes Gardenia' },
  { slug: 'taiwan-interior',              loai: 'chung-cu',  name: 'Taiwan Interior' },
  { slug: 'spa-wellness-hanoi',           loai: 'spa',       name: 'Spa & Wellness in Hanoi' },
  { slug: 'saigon-little-house',          loai: 'nha-pho',   name: 'Saigon Little House' },
  { slug: 'modern-classic-apartment',     loai: 'chung-cu',  name: 'Modern Classic Apartment' },
  { slug: 'gold',                         loai: 'chung-cu',  name: 'Gold' },
  { slug: 'apartment-in-hanoi',           loai: 'chung-cu',  name: 'Apartment in Hanoi' },
  { slug: 'hotel-deluxe-room',            loai: 'khach-san', name: 'Hotel Deluxe Room' },
  { slug: 'indochine-apartment-2',        loai: 'chung-cu',  name: 'Indochine Apartment II' },
  { slug: 'indochine-apartment-3',        loai: 'chung-cu',  name: 'Indochine Apartment III' },
  { slug: 'indochine-bedroom',            loai: 'phong',     name: 'Indochine Bedroom' },
  { slug: 'luxury-interior',              loai: 'chung-cu',  name: 'Luxury Interior' },
  { slug: 'beauty-clinic-ham-long',       loai: 'spa',       name: 'Beauty Clinic – Ham Long, Hà Nội' },
  { slug: 'apartment-in-dark-tone',       loai: 'chung-cu',  name: 'Apartment in Dark Tone' },
  { slug: 'studio-apartment-chill-time',  loai: 'chung-cu',  name: 'Studio Apartment – Chill Time' },
  { slug: 'minimalism-apartment',         loai: 'chung-cu',  name: 'Minimalism Apartment I' },
  { slug: 'minimalism-apartment-2',       loai: 'chung-cu',  name: 'Minimalism Apartment II' },
  { slug: 'minimalism-apartment-3',       loai: 'chung-cu',  name: 'Minimalism Apartment III' },
  { slug: 'apartment-in-grey',            loai: 'chung-cu',  name: 'Apartment in Grey' },
  { slug: 'colorful-apartment',           loai: 'chung-cu',  name: 'Colorful Apartment' },
  { slug: 'd3studio-design',              loai: 'chung-cu',  name: 'D3 Studio Design' },
  { slug: 'linh-nam-apartment',           loai: 'chung-cu',  name: 'Mr. Tu – Linh Nam, Hà Nội' },
  { slug: 'neo-classic',                  loai: 'chung-cu',  name: 'Neo Classic' },
  { slug: 'neoclassic-apartment',         loai: 'chung-cu',  name: 'Neoclassic Apartment' },
  { slug: 'nov-apartment',                loai: 'chung-cu',  name: 'Nov Apartment' },
  { slug: 'scandinavian-apartment-hanoi', loai: 'chung-cu',  name: 'Scandinavian Apartment in Hanoi' },
  { slug: 'scandinavian-apartment',       loai: 'chung-cu',  name: 'Scandinavian Apartment' },
  { slug: 'small-apartment-hanoi',        loai: 'chung-cu',  name: 'Small Apartment in Hanoi' },
  { slug: 'small-apartment',              loai: 'chung-cu',  name: 'Small Apartment' },
  { slug: 'vinhomes-hai-phong',           loai: 'chung-cu',  name: 'Vinhomes Hải Phòng' },
  { slug: 'modern-farmhouse',             loai: 'nha-pho',   name: 'Modern Farmhouse' },
  { slug: 'hotel-double-room',            loai: 'khach-san', name: 'Hotel Double Room' },
  { slug: 'hotel-bedroom',                loai: 'khach-san', name: 'Hotel Bedroom' },
  { slug: 'working-space',                loai: 'van-phong', name: 'Working Space' },
  { slug: 'luxury-living-room',           loai: 'phong',     name: 'Luxury Living Room' },
  { slug: 'luxury-bedroom',               loai: 'phong',     name: 'Luxury Bedroom' },
  { slug: 'luxury-bathroom-wardrobe',     loai: 'phong',     name: 'Luxury Bathroom & Wardrobe – Mr. Ngoc Anh' },
  { slug: 'bedroom-3d-concept',           loai: 'phong',     name: 'Bedroom in 3D Concept' },
  { slug: 'bedroom',                      loai: 'phong',     name: 'Bedroom' },
  { slug: 'bedroom-d3-studio',            loai: 'phong',     name: 'Bedroom by D3 Studio' },
  { slug: 'classic-teen-bedroom',         loai: 'phong',     name: 'Classic Bedroom – Teen Boy' },
  { slug: 'classic-kitchen',              loai: 'phong',     name: 'Classic Kitchen' },
  { slug: 'modern-kitchen',               loai: 'phong',     name: 'Modern Kitchen' },
  { slug: 'sauna-bathroom',               loai: 'phong',     name: 'Sauna Bathroom' },
  { slug: 'bright-apartment',             loai: 'chung-cu',  name: 'Bright Apartment' }
]

// Dự án chưa có ảnh thì không hiện
export const PROJECTS_LIST = PROJECTS
  .filter(p => FOLDER_IMAGES[p.slug])
  .map(p => ({ ...p, images: FOLDER_IMAGES[p.slug], cover: FOLDER_IMAGES[p.slug][0].src }))

export const projectBySlug = slug => PROJECTS_LIST.find(p => p.slug === slug) || null
