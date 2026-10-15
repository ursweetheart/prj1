/* ═══════════════════════════════════════════════════════════════════════
 * Danh sách không gian cho trang chủ và trang công trình.
 * Lấy các không gian ĐÃ ĐĂNG từ API; nếu không gọi được API (ví dụ bản tĩnh
 * trên GitHub Pages không có backend) thì dùng dữ liệu minh hoạ trong src/data.
 * Tải một lần, dùng chung giữa các trang.
 * ═══════════════════════════════════════════════════════════════════ */
import { reactive } from 'vue'
import { SPACES } from '@/data'
import { listPublished, toCard } from '@/api'

const state = reactive({ spaces: [], source: 'loading' }) // source: loading | api | demo
let loading = null

export function usePortfolio() {
  loading ??= listPublished()
    .then(rows => { state.spaces = rows.map(toCard); state.source = 'api' })
    .catch(() => { state.spaces = SPACES; state.source = 'demo' })
  return state
}
