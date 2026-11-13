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
export const BACKEND = ORIGIN || 'http://localhost:8001'
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
    const err = new Error(res.status === 404 ? 'Không tìm thấy dữ liệu này.'
      : typeof detail === 'string' ? detail : 'Máy chủ không phản hồi (' + res.status + ').')
    err.status = res.status
    err.detail = detail // 422: [{loc, msg}], so a form can put each error under its field
    throw err
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
// AI-proposed dimensions awaiting the lead architect (seq-15); accepting back-tags the library, so it takes a while
export const listCandidates = () => get('/taxonomy/candidates')
export const acceptCandidate = (id, ten, gia_tri) => request('POST', `/taxonomy/candidates/${id}/accept`, { body: { ten, gia_tri } })
export const rejectCandidate = id => request('POST', `/taxonomy/candidates/${id}/reject`)

export const searchSpaces = (q, k = 12) => get('/search', { q, k })
export function searchByImage(file, k = 12) {
  const form = new FormData()
  form.append('file', file)
  return request('POST', '/search/image', { params: { k }, form })
}
export const getSpace = id => get('/spaces/' + id)

/* Behaviour signal for taxonomy discovery (UC21). The visitor's answer on the consent banner lives in localStorage;
 * without a 'yes' the server only counts the view for the day. Fire-and-forget: tracking never breaks a page. */
const CONSENT_KEY = 'd3_dong_y_thu_thap'
export const consent = {
  get() { try { return localStorage.getItem(CONSENT_KEY) } catch { return null } },
  set(v) { try { localStorage.setItem(CONSENT_KEY, v) } catch { /* private mode: ask again next visit */ } }
}
export function visitId() { // random per browser tab session, never tied to an account
  try {
    let id = sessionStorage.getItem('d3_phien')
    if (!id) sessionStorage.setItem('d3_phien', id = crypto.randomUUID().replaceAll('-', ''))
    return id
  } catch { return null }
}
export function trackView(spaceId) {
  const yes = consent.get() === 'yes' && visitId()
  request('POST', '/events', { body: { loai: 'xem_khong_gian', dong_y: !!yes, phien_id: yes || null, space_id: yes ? spaceId : null } })
    .catch(() => {}) // 204 has no JSON body; errors are not the visitor's problem
}
export const getSimilar = (id, k = 8) => get('/spaces/' + id + '/similar', { k })

export const SPACE_TYPES = Object.keys(SPACE_VI)
export const STYLES = [...Object.keys(PC), 'Khac']
// QT-01; 'cleared' = the client allowed publishing the photos
export const NEXT_STATUS = { draft: 'in_review', in_review: 'approved', approved: 'cleared', cleared: 'published' }
export const STATUS_VI = { draft: 'Nháp', in_review: 'Chờ duyệt', approved: 'Đã duyệt', cleared: 'Đã xác nhận quyền', published: 'Đã đăng' }
export const EDITORS = [...STAFF, 'content'] // content may only edit caption / alt text of spaces in review

export const listSpaces = (params = {}) => get('/spaces', { limit: 200, ...params })
export const reviewSpace = (id, body) => request('PATCH', '/spaces/' + id, { body })
export const advanceSpaces = (ids, rightsConfirmed = false) =>
  request('POST', '/spaces/advance', { body: { space_ids: ids, rights_confirmed: rightsConfirmed } })
export const setTags = body => request('PUT', '/spaces/tags', { body }) // {space_ids | project, dimension, values}
export const projectOf = relativePath => relativePath.split('/')[0]

export function ingestSpace(file, project) {
  const form = new FormData()
  form.append('file', file)
  form.append('project', project)
  return request('POST', '/spaces/ingest', { form })
}

/* One request per file, in order: the server runs the pipeline on a single GPU.
 * A failed file is reported and the rest still go up. */
export async function uploadAll(files, project, onDone = () => {}) {
  const failed = []
  for (const [i, f] of [...files].entries()) {
    try { await ingestSpace(f, project) } catch (e) { failed.push({ name: f.name, error: e.message }) }
    onDone(i + 1)
  }
  return failed
}

// detector objects (anchor in 0..1) -> the {x, y, label} HotspotImage draws, in percent
export const hotspotsOf = s => ((s.hotspots && s.hotspots.objects) || []).map(o => ({
  x: o.hotspot_anchor[0] * 100, y: o.hotspot_anchor[1] * 100,
  label: o.label_vi || o.label, kind: o.service || 'Món đồ trong ảnh', price: null
}))
export const listLeads = (params = {}) => get('/leads', params)
/* phien_id + gui_ho_so: the visitor accepted the banner and ticked "send what I viewed" (lead-intake) */
export const sendChat = (message, history, contact, sendViews = false) =>
  request('POST', '/chat', { body: { message, history, ...(contact ? { contact } : {}), ...viewsConsent(sendViews) } })
export const createLead = body => request('POST', '/leads', { body: { ...body, ...viewsConsent(body.gui_ho_so) } })
function viewsConsent(ticked) { // the session id goes out only with both consents; the server checks again
  const id = ticked && consent.get() === 'yes' && visitId()
  return id ? { phien_id: id, gui_ho_so: true } : { gui_ho_so: false }
}
/* Every published space, for the portfolio grid (the API caps one page at 200) */
export const listPublished = () => get('/spaces', { review_status: 'published', limit: 200 })
