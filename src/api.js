/* Client for the D3 Studio API (FastAPI, see backend/api.py). */
import { reactive } from 'vue'
import { createCollector, deviceType, trafficSource } from '@/lib/collector'

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
  if (res.status === 204) return null // DELETE and /events answer with no body
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail
    const err = new Error(res.status === 404 ? 'Không tìm thấy dữ liệu này.'
      : typeof detail === 'string' ? detail
        : typeof detail?.msg === 'string' ? detail.msg // e.g. {thieu: [...], msg: 'Thiếu: Phong cách'} (publishing-workflow)
          : 'Máy chủ không phản hồi (' + res.status + ').')
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
/* account-invites-reset: invitations (admin) and password links (public). The link code travels in the body, never the URL */
export const inviteUser = (email, role, ho_ten = '') => request('POST', '/users/invite', { body: { email, role, ...(ho_ten.trim() ? { ho_ten } : {}) } })
// class-6 NguoiDung.ho_ten (admin-tools): the admin sets anyone's, a signed-in user their own
export const setUserName = (id, ho_ten) => request('PATCH', '/users/' + id, { body: { ho_ten } })
export async function setMyName(ho_ten) { await request('PATCH', '/auth/me', { body: { ho_ten } }); return loadUser() }
export const resendInvite = id => request('POST', '/users/' + id + '/invite/resend')
export const cancelInvite = id => request('POST', '/users/' + id + '/invite/cancel')
export const forgotPassword = email => request('POST', '/auth/forgot', { body: { email } })
export const linkInfo = ma => request('POST', '/auth/link-info', { body: { ma } })
export async function setPasswordFromLink(ma, matKhau) {
  const r = await request('POST', '/auth/set-password', { body: { ma, mat_khau: matKhau } })
  setToken(r.access_token)
  return loadUser()
}

export async function login(email, password) {
  const res = await fetch(API + '/auth/login', { method: 'POST', body: new URLSearchParams({ username: email, password }) })
  if (!res.ok) {
    const detail = res.status === 403 ? (await res.json().catch(() => ({}))).detail : null // 403: the account is locked
    throw new Error(res.status === 401 ? 'Sai email hoặc mật khẩu.' : detail || 'Không đăng nhập được (' + res.status + ').')
  }
  setToken((await res.json()).access_token)
  return loadUser()
}
export async function register(email, password, ho_ten = '') {
  await request('POST', '/auth/register', { body: { email, password, ...(ho_ten.trim() ? { ho_ten } : {}) } })
  return login(email, password)
}
export const logout = () => setToken(null)
export const hasRole = roles => !!session.user && roles.includes(session.user.role)

export const imageUrl = path => ORIGIN + '/images/' + encodeURI(path)
export const spaceLabel = type => SPACE_VI[type] || 'Không gian'

/* API row -> shape SpaceCard expects */
/* publishing-workflow (act-1): the optimised WebP copies as a srcset; the original closes the list at its own width.
   No copies (an old photo or a search hit without them) -> '' and the <img> keeps its src. */
export function imageSrcset(r) {
  const sizes = Object.entries(r?.kich_thuoc || {}).sort((a, b) => a[0] - b[0])
  if (!sizes.length) return ''
  const list = sizes.map(([w, rel]) => `${ORIGIN}/images/${encodeURI(rel)} ${w}w`)
  if (r.chieu_rong) list.push(`${imageUrl(r.relative_path)} ${r.chieu_rong}w`)
  return list.join(', ')
}

export const toCard = r => ({
  id: 'ai-' + r.id,
  apiId: r.id,
  path: r.relative_path,
  projectName: r.relative_path.split('/')[0].replace(/_/g, ' '),
  space: spaceLabel(r.space_type),
  img: imageUrl(r.relative_path),
  srcset: imageSrcset(r),
  why: r.ly_do || [], // search-explanations: why this result fits (shared or named labels)
  published: r.ngay_xuat_ban || null, viewRank: r.hang_xem ?? null, styleName: PC[r.design_style] || String(r.design_style || '').toLowerCase(), // BFD 1.2 sorts
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
/* seq-10 / BFD 1.1-1.2 (search-explanations): project filter. sel {dimension: [codes]}, area [from, to] (m2, either empty) */
export function projectFilterParams(sel = {}, area = [], sort = 'moi_nhat') {
  const pairs = []
  for (const dim of ['phong_cach', 'loai_cong_trinh', 'muc_dau_tu']) for (const v of sel[dim] || []) pairs.push([dim, v])
  if (area[0] !== undefined && area[0] !== null && area[0] !== '') pairs.push(['dien_tich_tu', String(area[0])])
  if (area[1] !== undefined && area[1] !== null && area[1] !== '') pairs.push(['dien_tich_den', String(area[1])])
  if (sort && sort !== 'moi_nhat') pairs.push(['sap_xep', sort])
  return pairs
}
export const filterProjects = (sel, area, sort) => get('/projects/filter', projectFilterParams(sel, area, sort))
// BFD 2.3 (visitor-touchpoints): a read-only snapshot of the current collection -> {ma, so_anh}
export const shareCollection = items => request('POST', '/collections/share', { body: { items } })
// seq-14 b6-b9 (admin-tools): the local detector's suggestions for one photo, nothing stored
export const detectObjects = id => request('POST', `/spaces/${id}/detect`)
export const getTaxonomy = () => get('/taxonomy')
// taxonomy admin (seq-15): the tree with usage counts and the change log; every write returns the changed row
export const getTaxonomyAdmin = () => get('/taxonomy/admin')
// account admin (seq-19, admin only): list, role, lock / unlock; the server refuses self-changes and the last admin
export const ROLE_VI = { visitor: 'Khách', architect: 'Kiến trúc sư', content: 'Nội dung', sales: 'Kinh doanh',
  lead_architect: 'KTS trưởng', admin: 'Quản trị viên' }
export const listUsers = (params = {}) => get('/users', params)
export const setUserRole = (id, role) => request('PATCH', '/users/' + id + '/role', { body: { role } })
export const lockUser = (id, lyDo) => request('POST', '/users/' + id + '/lock', { body: { ly_do: lyDo } })
export const unlockUser = id => request('POST', '/users/' + id + '/unlock')
// assistant knowledge (seq-16): entries the chatbot answers from, and the questions it could not answer
export const listKnowledge = (params = {}) => get('/knowledge', params)
export const createKnowledge = body => request('POST', '/knowledge', { body })
export const updateKnowledge = (id, body) => request('PATCH', '/knowledge/' + id, { body })
export const setKnowledgeStatus = (id, trangThai) => request('POST', '/knowledge/' + id + '/status', { body: { trang_thai: trangThai } })
export const deleteKnowledge = id => request('DELETE', '/knowledge/' + id)
export const knowledgeGaps = () => get('/knowledge/gaps')
// forbidden topics (seq-3 b15): keywords the assistant must not discuss
export const listTopics = () => get('/forbidden-topics')
export const createTopic = body => request('POST', '/forbidden-topics', { body })
export const updateTopic = (id, body) => request('PATCH', '/forbidden-topics/' + id, { body })
export const deleteTopic = id => request('DELETE', '/forbidden-topics/' + id)
export const tryTopics = text => request('POST', '/forbidden-topics/try', { body: { text } })
export const dismissGaps = ids => request('POST', '/knowledge/gaps/dismiss', { body: { ids } })
export const addDimension = body => request('POST', '/taxonomy', { body })
export const editDimension = (id, body) => request('PATCH', '/taxonomy/' + id, { body })
export const addValue = (dimId, body) => request('POST', '/taxonomy/' + dimId + '/values', { body })
export const editValue = (id, body) => request('PATCH', '/taxonomy/values/' + id, { body })
export const mergeValue = (id, targetId) => request('POST', '/taxonomy/values/' + id + '/merge', { body: { target_id: targetId } })
// AI-proposed dimensions awaiting the lead architect (seq-15); accepting back-tags the library, so it takes a while
export const listCandidates = () => get('/taxonomy/candidates')
export const acceptCandidate = (id, ten, gia_tri) => request('POST', `/taxonomy/candidates/${id}/accept`, { body: { ten, gia_tri } })
export const rejectCandidate = id => request('POST', `/taxonomy/candidates/${id}/reject`)
/* review-tag-autocomplete: a reviewer's word -> new value, synonym of an existing one, or nothing */
export const acceptValueCandidate = (id, body) => request('POST', `/taxonomy/value-candidates/${id}/accept`, { body })
export const mapValueCandidate = (id, gia_tri_id) => request('POST', `/taxonomy/value-candidates/${id}/map`, { body: { gia_tri_id } })
export const rejectValueCandidate = id => request('POST', `/taxonomy/value-candidates/${id}/reject`)

/* search-explanations: the API answers {ket_qua, ...}; callers keep getting the list, and the rest (constraints taken
   from a description, a rewording hint, an uploaded photo's traits or refusal) goes to lastSearch for SearchNote.vue.
   dfd-2-1 1.3: a search is recorded by kind and number of results, never its words or photo. */
export const lastSearch = reactive({ kind: null, rang_buoc: [], goi_y: null, noi_that: null, thong_bao: null, dac_diem: {} })
export const clearSearch = () => Object.assign(lastSearch, { kind: null, rang_buoc: [], goi_y: null, noi_that: null, thong_bao: null, dac_diem: {} })
export async function searchSpaces(q, k = 12) {
  const r = await get('/search', { q, k })
  const rows = Array.isArray(r) ? r : r.ket_qua
  Object.assign(lastSearch, { kind: 'mo_ta', rang_buoc: r.rang_buoc || [], goi_y: r.goi_y || null, noi_that: null, thong_bao: null, dac_diem: {} })
  if (String(q || '').trim()) trackEvent('tim_kiem', { doi_tuong: 'mo_ta', so_ket_qua: rows.length })
  return rows
}
export async function searchByImage(file, k = 12) {
  const form = new FormData()
  form.append('file', file)
  const r = await request('POST', '/search/image', { params: { k }, form })
  const rows = Array.isArray(r) ? r : r.ket_qua
  Object.assign(lastSearch, { kind: 'anh', rang_buoc: [], goi_y: null, noi_that: r.noi_that ?? true,
    thong_bao: r.thong_bao || null, dac_diem: r.dac_diem || {} })
  trackEvent('tim_kiem', { doi_tuong: 'anh', so_ket_qua: rows.length })
  return rows
}
export const getSpace = id => get('/spaces/' + id)

/* Behaviour signals (UC21). The visitor's answer on the consent notice lives in localStorage (act-7):
 *   'yes'        analytics and personalisation
 *   'phan_tich'  analytics only (Tùy chỉnh)
 *   'no'         neither: the server only counts each event type for the day
 * Events leave in batches (lib/collector.js, seq-4 b2-b3). Fire-and-forget: tracking never breaks a page. */
const CONSENT_KEY = 'd3_dong_y_thu_thap'
const DEVICE_KEY = 'd3_thiet_bi'
const webStore = (kind, fn) => { try { return fn(kind === 'local' ? localStorage : sessionStorage) } catch { return null } }
export const consent = {
  get() { return webStore('local', s => s.getItem(CONSENT_KEY)) },
  set(v) {
    webStore('local', s => s.setItem(CONSENT_KEY, v))
    if (!consent.analyticsFor(v)) webStore('local', s => s.removeItem(DEVICE_KEY)) // the device id exists only under consent
    try { window.dispatchEvent(new CustomEvent('d3-consent-changed', { detail: v })) } catch { /* no window in tests */ }
  },
  analyticsFor: v => v === 'yes' || v === 'phan_tich',
  analytics() { return consent.analyticsFor(consent.get()) },
  personal() { return consent.get() === 'yes' },
}
export function visitId() { // random per browser tab session, never tied to an account
  return webStore('session', s => {
    let id = s.getItem('d3_phien')
    if (!id) s.setItem('d3_phien', id = crypto.randomUUID().replaceAll('-', ''))
    return id
  })
}
function deviceId() { // class-4 ma_thiet_bi_an_danh: random, kept by this browser only while analytics consent is on
  if (!consent.analytics()) return null
  return webStore('local', s => {
    let id = s.getItem(DEVICE_KEY)
    if (!id) s.setItem(DEVICE_KEY, id = crypto.randomUUID().replaceAll('-', ''))
    return id
  })
}
function source() { // fixed for the tab session: where the visit came from
  return webStore('session', s => {
    let v = s.getItem('d3_nguon')
    if (!v) s.setItem('d3_nguon', v = trafficSource(document.referrer, location.search, location.hostname))
    return v
  }) || 'truc_tiep'
}
const collector = createCollector({
  send: body => {
    try {
      fetch(API + '/events', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), keepalive: true })
        .catch(() => {}) // errors are not the visitor's problem
    } catch { /* never the visitor's problem */ }
  },
  context: () => {
    const consented = consent.analytics() && !!visitId()
    return consented
      ? { consented, phien_id: visitId(), ma_thiet_bi: deviceId(), nguon: source(), ca_nhan_hoa: consent.personal(),
          thiet_bi: deviceType(window.innerWidth, !!window.matchMedia?.('(pointer: coarse)').matches) }
      : { consented: false }
  },
})
if (typeof document !== 'undefined') source() // where the visit came from, read before any reload replaces the referrer
/* Leaving or hiding the page sends what is waiting (seq-4: "hoặc khi rời trang"). lib/pageTracking.js calls it after
   it has recorded the page view being left, so that view leaves with the batch. */
export const flushEvents = () => collector.flush()

/* act-7 "Xóa dữ liệu của tôi": this browser's sessions (the tab's and every one with its device id) and their events.
   Waiting events are dropped first, so nothing is stored after the deletion; then the browser starts afresh. */
export async function forgetMe() {
  collector.clear()
  const phien_id = webStore('session', s => s.getItem('d3_phien'))
  const ma_thiet_bi = webStore('local', s => s.getItem(DEVICE_KEY))
  const r = phien_id || ma_thiet_bi
    ? await request('POST', '/privacy/xoa-du-lieu', { body: { phien_id, ma_thiet_bi } })
    : { so_phien: 0, so_su_kien: 0 }
  webStore('session', s => s.removeItem('d3_phien'))
  webStore('local', s => s.removeItem(DEVICE_KEY))
  return r
}
export const openConsent = () => window.dispatchEvent(new Event('d3-consent-open'))

/* act-3 homepage "Đang được quan tâm": the session is sent only when the visitor allowed personalisation (act-7) */
export const getHomeSuggestions = () => get('/home/suggestions', consent.personal() && visitId() ? { phien_id: visitId() } : {})
export const getHomeSettings = () => get('/analytics/home-suggestions')
export const setHomeSetting = (gia_tri, che_do) => request('PUT', '/analytics/home-suggestions', { body: { gia_tri, che_do } })

function track(loai, spaceId) { // photo events: callers already skip staff
  collector.push(loai, { space_id: spaceId })
}
/* behaviour-events (UC21): page views with time and scroll, CTA clicks, forms, chat, share, filters, searches.
   Never for staff (a signed-in account still loading could be staff, so it waits). */
export function trackEvent(loai, fields = {}) {
  if (session.token && (!session.user || session.user.role !== 'visitor')) return
  collector.push(loai, fields)
}
export const trackView = spaceId => track('xem_khong_gian', spaceId)
export const trackSave = spaceId => track('luu_anh', spaceId) // trend-dashboard: a save is a stronger signal
export const trackQuizPick = spaceId => track('chon_trac_nghiem', spaceId) // style-quiz: not in the interest score

/* seq-2 b12/b14: similar spaces shown, and one of them opened (pageTracking asks takeSimilarPick on each space page) */
let lastSimilar = null
export async function getSimilar(id, k = 8) {
  const rows = await get('/spaces/' + id + '/similar', { k })
  if (rows.length) {
    trackEvent('xem_goi_y_tuong_tu', { space_id: Number(id) })
    lastSimilar = { src: Number(id), ids: new Set(rows.map(r => r.id)) }
  }
  return rows
}
export function takeSimilarPick(id) { // -> the source space when `id` was one of the similar spaces shown last
  const src = lastSimilar && lastSimilar.ids.has(Number(id)) ? lastSimilar.src : null
  if (src !== null) lastSimilar = null
  return src
}

// QT-01; 'cleared' = the client allowed publishing the photos
export const NEXT_STATUS = { draft: 'editing', editing: 'in_review', in_review: 'approved', approved: 'cleared', cleared: 'published' }
export const STATUS_VI = { draft: 'Nháp', editing: 'Chờ biên tập', in_review: 'Chờ duyệt', approved: 'Đã duyệt', cleared: 'Đã xác nhận quyền', published: 'Đã đăng',
  noi_bo: 'Lưu nội bộ' } // noi_bo: the client refused publishing; final, never public (review-return-reject)
// backward paths, lead architect / admin, always with a reason (5-500 characters); all or nothing
export const RETURNABLE = ['editing', 'in_review', 'approved', 'cleared']
export const returnSpaces = (ids, lyDo) => request('POST', '/spaces/return', { body: { space_ids: ids, ly_do: lyDo } })
export const keepInternal = (ids, lyDo) => request('POST', '/spaces/keep-internal', { body: { space_ids: ids, ly_do: lyDo } })
export const reopenSpaces = (ids, lyDo) => request('POST', '/spaces/reopen', { body: { space_ids: ids, ly_do: lyDo } })
/* unpublish-photos: published -> draft (to fix) or noi_bo (the client withdrew consent), always with a reason */
export const unpublishSpaces = (ids, lyDo, giuNoiBo = false) => request('POST', '/spaces/unpublish', { body: { space_ids: ids, ly_do: lyDo, giu_noi_bo: giuNoiBo } })
export const EDITORS = [...STAFF, 'content'] // content may only edit caption / alt text of spaces in review

export const listSpaces = (params = {}) => get('/spaces', { limit: 200, ...params })
export const reviewSpace = (id, body) => request('PATCH', '/spaces/' + id, { body })
/* review-tag-autocomplete: a room type / style the list doesn't have -> {kind: existing|suggested, ...} */
export const suggestValue = (id, chieu, text, force = false) =>
  request('POST', `/spaces/${id}/suggest-value`, { body: { chieu, text, force } })
/* hotspot-items: hotspots edited by hand and the item library (seq-14) */
export const saveHotspots = (id, hotspots) => request('PUT', '/spaces/' + id + '/hotspots', { body: { hotspots } })
export const searchItems = (q = '', limit = 200) => get('/items', { q, limit })
export const createItem = body => request('POST', '/items', { body })
export const updateItem = (id, body) => request('PATCH', '/items/' + id, { body })
export const deleteItem = id => request('DELETE', '/items/' + id)
export const itemSpaces = id => get('/items/' + id + '/spaces')
export const itemServices = () => get('/items/services') // service packages an item may point to
export const advanceSpaces = (ids, rightsConfirmed = false) =>
  request('POST', '/spaces/advance', { body: { space_ids: ids, rights_confirmed: rightsConfirmed } })
export const setTags = body => request('PUT', '/spaces/tags', { body }) // {space_ids | project, dimension, values}
export const projectOf = relativePath => relativePath.split('/')[0]

export const ingestTasks = ids => get('/spaces/ingest/tasks', { ids: ids.join(',') })

/* labelling-queue-feedback (seq-1 b5-b6, b16): follow queued tasks until each is done or failed.
   fetchStatus(ids) -> [{id, trang_thai, loi}]; a failed poll (network blip) is simply retried on the next turn. */
export async function pollTasks(tasks, fetchStatus, onProgress = () => {}, wait = ms => new Promise(r => setTimeout(r, ms)), every = 2000) {
  const name = Object.fromEntries(tasks.map(t => [t.id, t.relative_path.split('/').pop()]))
  const failed = []
  let open = tasks.map(t => t.id), ok = 0
  onProgress(0, tasks.length)
  while (open.length) {
    await wait(every)
    let st
    try { st = await fetchStatus(open) } catch { continue }
    for (const s of st) {
      if (s.trang_thai === 'xong') ok++
      else if (s.trang_thai === 'loi') failed.push({ name: name[s.id], error: s.loi })
    }
    open = st.filter(s => s.trang_thai === 'dang_xu_ly').map(s => s.id)
    onProgress(tasks.length - open.length, tasks.length)
  }
  return { ok, failed }
}

/* One request queues every photo and comes back at once; then the queue is followed (seq-1 b2-b6).
   -> { total, ok, failed: [{name, error}] } with refused files (wrong type or size) among the failures. */
export async function uploadAll(files, project, onProgress = () => {}) {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  form.append('project', project)
  const { tasks, refused } = await request('POST', '/spaces/ingest', { form })
  const done = await pollTasks(tasks, ingestTasks, onProgress)
  return { total: tasks.length, ok: done.ok, failed: [...refused.map(r => ({ name: r.name, error: r.ly_do })), ...done.failed] }
}

// detector objects (anchor in 0..1) -> the {x, y, label} HotspotImage draws, in percent
/* visitor-services-hotspots: the card shows the name, the item's other spaces (itemId) and the service as a small link */
export const hotspotsOf = s => ((s.hotspots && s.hotspots.objects) || []).map(o => ({
  x: o.hotspot_anchor[0] * 100, y: o.hotspot_anchor[1] * 100,
  label: o.label_vi || o.label, raw: o.label || '', itemId: Number.isInteger(o.mon_do_id) ? o.mon_do_id : null,
  service: o.service || null
}))
export const getServices = () => get('/services') // public: service packages in use, for /dich-vu
export const listLeads = (params = {}) => get('/leads', params)
/* phien_id + gui_ho_so: the visitor accepted the banner and ticked "send what I viewed" (lead-intake) */
/* chat-history: the conversation id goes with every message; the session id goes whenever the banner was accepted
   (as /events does) so the conversation is linked, while a lead still attaches views only when the box is ticked */
export const sendChat = (message, history, contact, sendViews = false, hoiThoaiId = null) => {
  const phien = consent.analytics() && visitId()
  return request('POST', '/chat', { body: { message, history, ...(contact ? { contact } : {}),
    ...(hoiThoaiId ? { hoi_thoai_id: hoiThoaiId } : {}), ...(phien ? { phien_id: phien } : {}), gui_ho_so: !!(phien && sendViews) } })
}
export const getChat = id => get('/chat/' + encodeURIComponent(id))
export const deleteChat = id => request('DELETE', '/chat/' + encodeURIComponent(id))
export const listConversations = (params = {}) => get('/conversations', params)
export const getConversation = id => get('/conversations/' + encodeURIComponent(id))
/* Saved collection (UC07) and design brief (UC08). The browser-or-account switch lives in lib/collection.js */
export const getMyCollection = () => get('/collections/me')
export const saveToCollection = (spaceId, ghiChu = null) =>
  request('PUT', '/collections/me/items/' + spaceId, { body: { ghi_chu: ghiChu || null } })
export const removeFromCollection = spaceId => request('DELETE', '/collections/me/items/' + spaceId)
export const mergeCollection = items => request('POST', '/collections/me/merge', { body: { items } })
export const getSharedCollection = code => get('/collections/shared/' + encodeURIComponent(code))

// style quiz (UC06, seq-12): answers = { cap: [[a, b], ...], chon: [id, ...] }; the server scores, never the client
export const getQuiz = () => get('/quiz')
export const postQuizResult = answers => request('POST', '/quiz/result', { body: answers })
export const getMyQuiz = () => get('/quiz/me') // null (204) when the account has no saved result
export const saveMyQuiz = answers => request('PUT', '/quiz/me', { body: answers })
export const getSpacesByIds = ids => ids.length ? get('/spaces', { ids: ids.join(','), limit: ids.length }) : Promise.resolve([])
export const sendBrief = body => request('POST', '/briefs', { body: { ...body, ...viewsConsent(body.gui_ho_so) } })
/* Trend dashboard (UC22): interest score, trends, totals; aggregates only */
export const getOverview = (days = 30) => get('/analytics/overview', { days })
export const getBehaviour = (days = 30) => get('/analytics/behaviour', { days }) // behaviour-events
export const getProjectStats = (days = 30, cuaToi = false) => get('/analytics/projects', { days, ...(cuaToi ? { cua_toi: true } : {}) })
export const getProjectDetail = (folder, days = 30) => get('/analytics/projects/' + encodeURIComponent(folder), { days })
export const getWeeklyOptIn = () => get('/me/weekly-report')
export const setWeeklyOptIn = nhan => request('PUT', '/me/weekly-report', { body: { nhan } })
export const listWeeklyReports = () => get('/reports/weekly')
export const previewWeeklyReport = () => get('/reports/weekly/preview')
export const testWeeklyReport = () => request('POST', '/reports/weekly/test')
export const createLead = body => request('POST', '/leads', { body: { ...body, ...viewsConsent(body.gui_ho_so) } })
function viewsConsent(ticked) { // the session id goes out only with both consents; the server checks again
  const id = ticked && consent.analytics() && visitId()
  return id ? { phien_id: id, gui_ho_so: true } : { gui_ho_so: false }
}
/* Every published space, for the portfolio grid; the API caps one page at 200, so read pages until a short one */
export async function listPublished() {
  const all = []
  for (let offset = 0; ; offset += 200) {
    const page = await get('/spaces', { review_status: 'published', limit: 200, offset })
    all.push(...page)
    if (page.length < 200) return all
  }
}
/* Published spaces of one project folder (slug with '-' -> '_'), ordered by file name */
export const getProjectSpaces = folder => get('/projects/' + folder + '/spaces')
