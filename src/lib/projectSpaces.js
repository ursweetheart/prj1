/* ═══════════════════════════════════════════════════════════════════════
 * Cầu nối giữa dự án tĩnh (src/assets/projects/<slug>/) và không gian AI ở backend.
 *
 *   ảnh  src/assets/projects/<slug>/<file>   ⟷   không gian  <folder>/<file>
 *   folder = slug đổi '-' thành '_'   (beaumont-lounge ⟷ beaumont_lounge)
 *
 * Mọi phần AI cho khách (mục "Không gian", dải ở trang chủ, link trong Lightbox) chỉ hiện
 * khi ai.state === 'on'. Không có backend (GitHub Pages, máy chủ tắt) thì im lặng, không báo lỗi.
 * ═══════════════════════════════════════════════════════════════════ */
import { reactive } from 'vue'
import { getProjectSpaces, getTaxonomy } from '@/api'

export const folderOf = slug => slug.replace(/-/g, '_')
export const slugOf = relativePath => relativePath.split('/')[0].replace(/_/g, '-')
export const fileOf = relativePath => relativePath.split('/').pop()
// đường dẫn ảnh trong trang dự án, mở sẵn Lightbox ở ảnh đó
export const projectPhotoHref = relativePath => '/du-an/' + slugOf(relativePath) + '?anh=' + encodeURIComponent(fileOf(relativePath))

const TIMEOUT = 4000
const withTimeout = p => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error('timeout')), TIMEOUT))])

/* Backend có trả lời không: hỏi /taxonomy một lần mỗi phiên */
export const ai = reactive({ state: 'unknown' }) // unknown | on | off
let probe = null
export function aiAvailable() {
  probe ??= withTimeout(getTaxonomy())
    .then(() => true, () => false)
    .then(ok => { ai.state = ok ? 'on' : 'off'; return ok })
  return probe
}

/* Không gian đã đăng của một dự án: Map tên file -> không gian; null khi không gọi được */
const cache = new Map()
export function loadProjectSpaces(slug) {
  if (!cache.has(slug)) {
    cache.set(slug, aiAvailable()
      .then(ok => ok ? withTimeout(getProjectSpaces(folderOf(slug))) : null)
      .then(rows => rows && new Map(rows.map(r => [fileOf(r.relative_path), r])))
      .catch(() => null))
  }
  return cache.get(slug)
}

/* Ảnh khách chọn ở dải trang chủ, chuyển sang /khong-gian để tìm (File không đi qua URL được) */
let pending = null
export const setPendingPhoto = file => { pending = file }
export const takePendingPhoto = () => { const f = pending; pending = null; return f }
