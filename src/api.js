/* Client for the D3 Studio API (FastAPI, see backend/api.py). */
import { reactive } from 'vue'

const SPACE_VI = {
  phong_khach: 'Phòng khách', phong_ngu_master: 'Phòng ngủ master', phong_ngu_phu: 'Phòng ngủ phụ',
  bep_va_an: 'Bếp & phòng ăn', phong_lam_viec: 'Phòng làm việc', sanh_thong_tang: 'Sảnh',
  ban_cong: 'Ban công', phong_tam: 'Phòng tắm', lounge_thuong_mai: 'Lounge', khac: 'Không gian'
}
// DB values -> facet ids used by the prototype's labels in data/index.js
const KG = {
  phong_khach: 'phong-khach', phong_ngu_master: 'phong-ngu', phong_ngu_phu: 'phong-ngu',
  bep_va_an: 'bep', lounge_thuong_mai: 'quay-bar', sanh_thong_tang: 'sanh',
  phong_lam_viec: 'phong-lam-viec', phong_tam: 'phong-tam', ban_cong: 'ban-cong'
}
// palette brightness / temperature -> the "Tông màu" facet
const TONE = { light: 'sang', dark: 'toi', warm: 'am', cool: 'lanh' }
const PC = {
  Indochine: 'indochine', Japandi: 'japandi', Wabi_sabi: 'wabi-sabi', Hien_dai: 'hien-dai',
  Tan_co_dien: 'tan-co-dien', Luxury: 'luxury', Toi_gian: 'toi-gian', Scandinavian: 'scandi'
}

/* ── session: JWT in localStorage, user read from /auth/me ─────────────── */
const KEY = 'd3_token'
const store = {
  get() { try { return localStorage.getItem(KEY) } catch { return null } },
  set(v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY) } catch { /* private mode */ } }
}
export const session = reactive({ token: store.get(), user: null })
// VITE_API_URL = origin of the hosted backend. Unset (dev): fetch goes through the Vite proxy under /api,
// but OAuth redirects leave the SPA, so they need the real address.
const ORIGIN = import.meta.env.VITE_API_URL || ''
const API = ORIGIN || '/api'
export const BACKEND = ORIGIN || 'http://localhost:8000'
export const STAFF = ['architect', 'lead_architect', 'admin']
export const APPROVERS = ['lead_architect', 'admin']
export const SALES = ['sales', 'lead_architect', 'admin']

async function request(method, path, { params, body, form } = {}) {
  const qs = params ? '?' + new URLSearchParams(params) : ''
  const headers = {}
  if (session.token) headers.Authorization = 'Bearer ' + session.token
  if (body) headers['Content-Type'] = 'application/json'
  const res = await fetch(API + path + qs, { method, headers, body: form || (body && JSON.stringify(body)) })
  if (res.status === 401 && session.token) setToken(null) // expired or revoked
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail
    if (res.status === 404) throw new Error('Không tìm thấy dữ liệu này.')
    throw new Error(typeof detail === 'string' ? detail : 'Máy chủ không phản hồi (' + res.status + ').')
  }
  return res.json()
}
const get = (path, params) => request('GET', path, { params })

function setToken(t) {
  session.token = t
  store.set(t)
  if (!t) session.user = null
  scheduleRefresh()
}

/* Sliding session: the JWT lives 60 min, so swap it for a fresh one shortly before it expires. */
export function tokenExpiry(token) { // ms since epoch, 0 when unreadable
  try { return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).exp * 1000 } catch { return 0 }
}
const REFRESH_BEFORE = 5 * 60 * 1000
let timer
function scheduleRefresh() {
  clearTimeout(timer)
  if (!session.token) return
  timer = setTimeout(refreshToken, Math.max(tokenExpiry(session.token) - Date.now() - REFRESH_BEFORE, 0))
}
async function refreshToken() {
  try { setToken((await request('POST', '/auth/refresh')).access_token) } catch { /* a 401 already signed the user out */ }
}
if (typeof document !== 'undefined') // timers are throttled in background tabs: re-check when the tab comes back
  document.addEventListener('visibilitychange', () => { if (!document.hidden) scheduleRefresh() })
scheduleRefresh()
export async function loadUser() {
  if (!session.token) return null
  try { session.user = await get('/auth/me') } catch { session.user = null }
  return session.user
}
/* OAuth callbacks come back to the site as  <base>#token=...  */
export function adoptTokenFromHash() {
  const m = location.hash.match(/^#token=([\w.-]+)/)
  if (!m) return
  setToken(m[1])
  history.replaceState(null, '', location.pathname + location.search)
}
export async function login(email, password) {
  const res = await fetch(API + '/auth/login', { method: 'POST', body: new URLSearchParams({ username: email, password }) })
  if (!res.ok) throw new Error(res.status === 401 ? 'Sai email hoặc mật khẩu.' : 'Không đăng nhập được (' + res.status + ').')
  setToken((await res.json()).access_token)
  return loadUser()
}
export async function register(email, password) {
  await request('POST', '/auth/register', { body: { email, password } })
  return login(email, password)
}
export const logout = () => setToken(null)
export const hasRole = roles => !!session.user && roles.includes(session.user.role)

export const imageUrl = path => ORIGIN + '/images/' + encodeURI(path)
export const spaceLabel = type => SPACE_VI[type] || 'Không gian'

/* API row -> shape SpaceCard expects */
export const toCard = r => ({
  id: 'ai-' + r.id,
  apiId: r.id,
  projectName: r.relative_path.split('/')[0].replace(/_/g, ' '),
  space: spaceLabel(r.space_type),
  img: imageUrl(r.relative_path),
  ratio: 'sq',
  khonggian: KG[r.space_type],
  phongcach: PC[r.design_style],
  tongmau: [TONE[r.brightness], TONE[r.temperature]].filter(Boolean),
  tags: r.tags || {} // {dimension: [value, ...]} from the taxonomy; what the filters match on
})

// a /taxonomy dimension -> the facet shape FacetPanel and useBrowse use
export const toFacet = d => ({
  id: d.ma_dinh_danh, label: d.ten,
  options: d.values.map(v => ({ id: v.ma_dinh_danh, label: v.ten }))
})
export const getTaxonomy = () => get('/taxonomy')

export const searchSpaces = (q, k = 12) => get('/search', { q, k })
export const getSpace = id => get('/spaces/' + id)
export const getSimilar = (id, k = 8) => get('/spaces/' + id + '/similar', { k })

export const SPACE_TYPES = Object.keys(SPACE_VI)
export const STYLES = [...Object.keys(PC), 'Khac']
export const NEXT_STATUS = { draft: 'in_review', in_review: 'approved', approved: 'published' }
export const STATUS_VI = { draft: 'Nháp', in_review: 'Chờ duyệt', approved: 'Đã duyệt', published: 'Đã đăng' }

export const listSpaces = (params = {}) => get('/spaces', { limit: 60, ...params })
export const reviewSpace = (id, body) => request('PATCH', '/spaces/' + id, { body })
export const listLeads = (params = {}) => get('/leads', params)
export const sendChat = (message, history, contact) =>
  request('POST', '/chat', { body: { message, history, ...(contact ? { contact } : {}) } })
/* Every published space, for the portfolio grid (the API caps one page at 200) */
export const listPublished = () => get('/spaces', { review_status: 'published', limit: 200 })
