/* ═══════════════════════════════════════════════════════════════════════
 * Page views with time and scroll, and CTA clicks, for the whole site (behaviour-events; UC21, class-4 SuKien).
 * One route hook and one click listener, so no page needs editing. Pages are stored by route pattern
 * (/bo-suu-tap/xem/:ma), never the real path, query or hash; staff pages are skipped.
 * ═══════════════════════════════════════════════════════════════════ */
import { trackEvent } from '@/api'

export const CTA = ['/lien-he', '/trac-nghiem']
const MAX_MS = 86_400_000

/* '/khong-gian/:id(\\d+)' -> '/khong-gian/:id'; only characters the API accepts */
export function routePattern(route) {
  const raw = route.matched?.length ? route.matched[route.matched.length - 1].path : route.path
  const p = (raw || '/').replace(/\([^)]*\)/g, '').toLowerCase()
  return /^\/[a-z0-9/:_-]{0,99}$/.test(p) ? p : null
}

/* the object a page is about: a project slug or a photo id, nothing else (never a share code) */
export function objectOf(pattern, params = {}) {
  if (pattern === '/du-an/:slug' && /^[a-z0-9-]{1,100}$/.test(params.slug || '')) return params.slug
  if (pattern === '/khong-gian/:id' && /^\d{1,12}$/.test(String(params.id || ''))) return String(params.id)
  return null
}

/* href of a clicked link -> its CTA target, or null. base: the app's base path ('/prj1/') */
export function ctaTarget(href, origin, base = '/') {
  let url
  try { url = new URL(href, origin) } catch { return null }
  if (url.origin !== origin) return null
  const b = base.endsWith('/') ? base.slice(0, -1) : base
  const path = (b && url.pathname.startsWith(b) ? url.pathname.slice(b.length) : url.pathname).replace(/\/$/, '') || '/'
  return CTA.includes(path) ? path : null
}

export function scrollFraction(scrollY, viewport, height) {
  if (!height || height <= viewport) return 1
  return Math.min(1, Math.max(0, (scrollY + viewport) / height))
}

export function startPageTracking(router, win = window) {
  let cur = null
  let started = false

  const open = route => {
    cur = null
    if (route.meta?.roles) return // staff pages
    const trang = routePattern(route)
    if (!trang) return
    const obj = objectOf(trang, route.params)
    cur = { trang, obj, loai: trang === '/du-an/:slug' ? 'xem_du_an' : 'xem_trang', t0: Date.now(), max: 0 }
    onScroll()
  }
  const close = () => {
    if (!cur) return
    const ms = Math.min(MAX_MS, Date.now() - cur.t0)
    trackEvent(cur.loai, { trang: cur.trang, ...(cur.obj ? { doi_tuong: cur.obj } : {}), thoi_gian_dung_ms: ms,
      do_sau_cuon: Math.round(cur.max * 1000) / 1000 })
    cur = null
  }
  function onScroll() {
    if (!cur) return
    const d = win.document.documentElement
    cur.max = Math.max(cur.max, scrollFraction(win.scrollY, win.innerHeight, d.scrollHeight))
  }

  router.afterEach((to, from) => {
    if (started && to.path === from.path) return // a hash or query change on the same page
    started = true
    close()
    open(to)
  })
  win.addEventListener('scroll', onScroll, { passive: true })
  win.document.addEventListener('visibilitychange', () => {
    if (win.document.visibilityState === 'hidden') close() // background time is not reading time
    else if (!cur) open(router.currentRoute.value)
  })
  win.document.addEventListener('click', e => {
    const a = e.target?.closest?.('a[href]')
    if (!a) return
    const target = ctaTarget(a.getAttribute('href'), win.location.origin, import.meta.env.BASE_URL || '/')
    if (!target) return
    const from = routePattern(router.currentRoute.value)
    trackEvent('bam_CTA', { doi_tuong: target, ...(from ? { trang: from } : {}) })
  }, true)
}
