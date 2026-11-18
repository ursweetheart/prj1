/* ═══════════════════════════════════════════════════════════════════════
 * Browser event collector (tracking-pipeline; seq-4 b2-b3, act-3 "Gửi sự kiện lên máy chủ theo lô").
 * Events wait in a local buffer and leave as one batch every 5 s, or at once when the page is hidden or left.
 * Each event keeps how long before sending it happened (cach_ms), so the server stores it at its real time.
 * The consent state is read when sending, so a choice changed meanwhile applies to the next send.
 * ═══════════════════════════════════════════════════════════════════ */

export const EVERY_MS = 5000
export const MAX_BATCH = 50
export const MAX_AGE_MS = 600_000

const SEARCH = /(^|\.)(google|bing|coccoc|yahoo|duckduckgo|yandex)\./
const SOCIAL = /(^|\.)(facebook|fb|instagram|zalo|tiktok|youtube|linkedin|pinterest|twitter|threads)\.|(^|\.)(t\.co|x\.com)$/

/* class-4 nguon_truy_cap: a short campaign name from utm_source, else where the visitor came from */
export function trafficSource(referrer, search = '', host = '') {
  const utm = new URLSearchParams(search).get('utm_source')
  const name = (utm || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40)
  if (name) return name
  let from
  try { from = new URL(referrer).hostname.toLowerCase() } catch { return 'truc_tiep' }
  if (!from || from === host) return 'truc_tiep'
  if (SEARCH.test(from)) return 'tim_kiem'
  if (SOCIAL.test(from)) return 'mang_xa_hoi'
  return 'gioi_thieu'
}

/* class-4 loai_thiet_bi */
export function deviceType(width, coarse) {
  if (coarse && width < 768) return 'di_dong'
  if (coarse && width < 1100) return 'may_tinh_bang'
  return 'may_tinh'
}

/* The body of one batch: session details and event details only with consent (otherwise only the types are sent,
   which the server just counts for the day). */
export function batchBody(events, now, ctx) {
  const su_kien = events.map(e => {
    const cach_ms = Math.min(MAX_AGE_MS, Math.max(0, now - e.at))
    return ctx.consented ? { ...e.fields, loai: e.loai, cach_ms } : { loai: e.loai }
  })
  if (!ctx.consented) return { dong_y: false, su_kien }
  return { dong_y: true, phien_id: ctx.phien_id, ...(ctx.ma_thiet_bi ? { ma_thiet_bi: ctx.ma_thiet_bi } : {}),
    nguon: ctx.nguon, thiet_bi: ctx.thiet_bi, ca_nhan_hoa: !!ctx.ca_nhan_hoa, su_kien }
}

/* send(body) posts one batch; context() -> {consented, phien_id, ma_thiet_bi, nguon, thiet_bi, ca_nhan_hoa} at send time */
export function createCollector({ send, context, now = () => Date.now(), schedule = (fn, ms) => setTimeout(fn, ms),
  cancel = id => clearTimeout(id) }) {
  let queue = []
  let timer = null
  const flush = () => {
    if (timer !== null) { cancel(timer); timer = null }
    if (!queue.length) return
    const all = queue
    queue = []
    const ctx = context()
    for (let i = 0; i < all.length; i += MAX_BATCH) send(batchBody(all.slice(i, i + MAX_BATCH), now(), ctx))
  }
  const push = (loai, fields = {}) => {
    queue.push({ loai, fields, at: now() })
    if (timer === null) timer = schedule(flush, EVERY_MS)
  }
  const clear = () => { queue = []; if (timer !== null) { cancel(timer); timer = null } }
  return { push, flush, clear, size: () => queue.length }
}
