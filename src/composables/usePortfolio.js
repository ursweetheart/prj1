/* ═══════════════════════════════════════════════════════════════════════
 * Danh sách không gian và bộ lọc cho trang chủ và trang công trình.
 * Lấy các không gian ĐÃ ĐĂNG và các chiều phân loại từ API; nếu không gọi được
 * API (ví dụ bản tĩnh trên GitHub Pages không có backend) thì dùng dữ liệu minh
 * hoạ trong src/data. Tải một lần, dùng chung giữa các trang.
 * ═══════════════════════════════════════════════════════════════════ */
import { reactive } from 'vue'
import { FACETS, SPACES } from '@/data'
import { getTaxonomy, listPublished, toCard, toFacet } from '@/api'

const state = reactive({ spaces: [], facets: [], source: 'loading' }) // source: loading | api | demo
let loading = null

export function usePortfolio() {
  loading ??= Promise.all([listPublished(), getTaxonomy()])
    .then(([rows, dims]) => {
      state.spaces = rows.map(toCard)
      state.facets = dims.filter(d => d.hien_thi_cho_khach).map(toFacet)
      state.source = 'api'
    })
    .catch(() => { state.spaces = SPACES; state.facets = FACETS; state.source = 'demo' })
  return state
}
