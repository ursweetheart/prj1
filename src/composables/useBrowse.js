/* ═══════════════════════════════════════════════════════════════════════
 * Lọc đa chiều + đếm kết quả thời gian thực + đồng bộ URL hash
 * ═══════════════════════════════════════════════════════════════════ */
import { reactive, computed, watch } from 'vue'
import { trackEvent } from '@/api'

/* behaviour-events: a filter choice as stable 'dimension:value' items, only the ones the API accepts */
export function filterValues(selected) {
  return Object.entries(selected || {})
    .filter(([k]) => /^[a-z0-9_]+$/.test(k))
    .flatMap(([k, vals]) => (vals || []).filter(v => /^[A-Za-z0-9_]+$/.test(v)).map(v => k + ':' + v))
    .sort()
}
const SETTLE_MS = 1500

/* BFD 1.2 (search-explanations): one sort for the explorer, shared with the control in FacetPanel and kept in the
   URL hash as sap_xep=... beside the filters. Newest first is the default. */
export const SORTS = [{ id: 'moi_nhat', label: 'Mới đăng nhất' }, { id: 'xem_nhieu', label: 'Xem nhiều nhất (30 ngày)' },
  { id: 'phong_cach', label: 'Theo phong cách' }]
export const browseSort = reactive({ key: 'moi_nhat' })
const last = v => (v === null || v === undefined ? 1 : 0) // missing values sort last
export function sortSpaces(list, key) {
  const by = {
    moi_nhat: (a, b) => last(a.published) - last(b.published) || String(b.published || '').localeCompare(String(a.published || '')),
    xem_nhieu: (a, b) => last(a.viewRank) - last(b.viewRank) || (a.viewRank || 0) - (b.viewRank || 0),
    phong_cach: (a, b) => String(a.styleName || '').localeCompare(String(b.styleName || ''), 'vi'),
  }[key]
  return by ? [...list].sort((a, b) => by(a, b) || String(a.id).localeCompare(String(b.id), 'en', { numeric: true })) : list
}

/* spaces, facets: getters. Facets come from /taxonomy (API) or data/index.js (demo). */
export function useBrowse(spaces, facets) {
  const all = () => spaces() || []
  const dims = () => facets() || []
  const selected = reactive({}) // facet id -> chosen option ids; filled lazily, facets may load later

  const readHash = () => {
    const h = location.hash.replace(/^#/, '')
    if (!h) return
    h.split('&').forEach(part => {
      const [k, v] = part.split('=')
      if (k === 'sap_xep') { if (SORTS.some(s => s.id === v)) browseSort.key = v; return }
      if (k && v) selected[k] = v.split(',').filter(Boolean)
    })
  }

  const writeHash = () => {
    const s = Object.entries(selected)
      .filter(([, v]) => v.length)
      .map(([k, v]) => k + '=' + v.join(','))
      .join('&')
    const sort = browseSort.key !== 'moi_nhat' ? 'sap_xep=' + browseSort.key : ''
    const all = [s, sort].filter(Boolean).join('&')
    const url = location.pathname + (all ? '#' + all : '')
    history.replaceState(null, '', url)
  }

  readHash()
  watch(selected, writeHash, { deep: true })
  watch(() => browseSort.key, writeHash)

  // ap_dung_bo_loc once the choice settles; the same choice is not sent twice in a row
  let timer = null
  let lastSent = filterValues(selected).join('|') // a choice opened from a link is not a new filter action
  watch(selected, () => {
    clearTimeout(timer)
    timer = setTimeout(() => {
      const vals = filterValues(selected)
      const key = vals.join('|')
      if (!vals.length || key === lastSent) return
      lastSent = key
      const base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
      const path = base && location.pathname.startsWith(base) ? location.pathname.slice(base.length) || '/' : location.pathname
      trackEvent('ap_dung_bo_loc', { gia_tri: vals.slice(0, 20), ...(/^\/[a-z0-9/_-]{0,99}$/.test(path) ? { trang: path } : {}) })
    }, SETTLE_MS)
  }, { deep: true })

  // API cards carry their taxonomy values in `tags`; demo cards carry them as plain fields
  const valueOf = (s, k) => (s.tags ? s.tags[k] : s[k])

  const matches = (s, sel) => dims().every(f => {
    const vals = sel[f.id] || []
    if (!vals.length) return true
    const v = valueOf(s, f.id)
    return Array.isArray(v) ? v.some(x => vals.includes(x)) : vals.includes(v)
  })

  const results = computed(() => sortSpaces(all().filter(s => matches(s, selected)), browseSort.key))

  /* Đếm kiểu facet: số kết quả nếu thêm lựa chọn này vào điều kiện hiện tại */
  const counts = computed(() => {
    const out = {}
    dims().forEach(f => {
      const cur = selected[f.id] || []
      out[f.id] = {}
      f.options.forEach(o => {
        const probe = { ...selected, [f.id]: cur.includes(o.id) ? cur : cur.concat(o.id) }
        out[f.id][o.id] = all().filter(s => matches(s, probe)).length
      })
    })
    return out
  })

  const activeChips = computed(() =>
    dims().flatMap(f => (selected[f.id] || []).map(v => ({
      fid: f.id, vid: v, label: (f.options.find(o => o.id === v) || {}).label || v
    }))))

  return {
    selected, results, counts, activeChips,
    toggle(fid, oid) {
      const a = (selected[fid] ||= []), i = a.indexOf(oid)
      if (i === -1) a.push(oid); else a.splice(i, 1)
    },
    clear(fid) { selected[fid] = [] },
    clearAll() { Object.keys(selected).forEach(k => { selected[k] = [] }) }
  }
}
