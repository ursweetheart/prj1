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
  if (res.status === 204) return null // DELETE and /events answer with no body
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
/* account-invites-reset: invitations (admin) and password links (public). The link code travels in the body, never the URL */
export const inviteUser = (email, role) => request('POST', '/users/invite', { body: { email, role } })
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
  path: r.relative_path,
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
function track(loai, spaceId) {
  const yes = consent.get() === 'yes' && visitId()
  request('POST', '/events', { body: { loai, dong_y: !!yes, phien_id: yes || null, space_id: yes ? spaceId : null } })
    .catch(() => {}) // errors are not the visitor's problem
}
/* behaviour-events (UC21): page views with time and scroll, CTA clicks, forms, chat, share, filters. Same consent rule as
   track(): details only with consent, otherwise just the day's count. Never for staff (a signed-in account still loading
   could be staff, so it waits). keepalive lets a page-leave event survive the tab closing. */
export function trackEvent(loai, fields = {}) {
  if (session.token && (!session.user || session.user.role !== 'visitor')) return
  const id = consent.get() === 'yes' && visitId()
  const body = id ? { loai, dong_y: true, phien_id: id, ...fields } : { loai, dong_y: false }
  try {
    fetch(API + '/events', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), keepalive: true })
      .catch(() => {})
  } catch { /* never the visitor's problem */ }
}
export const trackView = spaceId => track('xem_khong_gian', spaceId)
export const trackSave = spaceId => track('luu_anh', spaceId) // trend-dashboard: a save is a stronger signal
export const trackQuizPick = spaceId => track('chon_trac_nghiem', spaceId) // style-quiz: not in the interest score
export const getSimilar = (id, k = 8) => get('/spaces/' + id + '/similar', { k })

// QT-01; 'cleared' = the client allowed publishing the photos
export const NEXT_STATUS = { draft: 'in_review', in_review: 'approved', approved: 'cleared', cleared: 'published' }
export const STATUS_VI = { draft: 'Nháp', in_review: 'Chờ duyệt', approved: 'Đã duyệt', cleared: 'Đã xác nhận quyền', published: 'Đã đăng',
  noi_bo: 'Lưu nội bộ' } // noi_bo: the client refused publishing; final, never public (review-return-reject)
// backward paths, lead architect / admin, always with a reason (5-500 characters); all or nothing
export const RETURNABLE = ['in_review', 'approved', 'cleared']
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
/* chat-history: the conversation id goes with every message; the session id goes whenever the banner was accepted
   (as /events does) so the conversation is linked, while a lead still attaches views only when the box is ticked */
export const sendChat = (message, history, contact, sendViews = false, hoiThoaiId = null) => {
  const phien = consent.get() === 'yes' && visitId()
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
/* Cost estimate (UC10) and its price table D8 */
export const estimate = body => request('POST', '/estimates', { body })
export const sendEstimate = body => request('POST', '/estimates/send', { body: { ...body, ...viewsConsent(body.gui_ho_so) } })
export const getPrices = () => get('/prices')
export const savePrice = (id, body) => request('PUT', '/prices/' + id, { body })
export const createLead = body => request('POST', '/leads', { body: { ...body, ...viewsConsent(body.gui_ho_so) } })
function viewsConsent(ticked) { // the session id goes out only with both consents; the server checks again
  const id = ticked && consent.get() === 'yes' && visitId()
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
