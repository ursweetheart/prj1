/* ═══════════════════════════════════════════════════════════════════════
 * Lọc đa chiều + đếm kết quả thời gian thực + đồng bộ URL hash
 * ═══════════════════════════════════════════════════════════════════ */
import { reactive, computed, watch } from 'vue'
import { FACETS, SPACES } from '@/data'

export function useBrowse() {
  const selected = reactive({})
  FACETS.forEach(f => { selected[f.id] = [] })

  const readHash = () => {
    const h = location.hash.replace(/^#/, '')
    if (!h) return
    h.split('&').forEach(part => {
      const [k, v] = part.split('=')
      if (selected[k] && v) selected[k] = v.split(',').filter(Boolean)
    })
  }

  const writeHash = () => {
    const s = Object.entries(selected)
      .filter(([, v]) => v.length)
      .map(([k, v]) => k + '=' + v.join(','))
      .join('&')
    const url = location.pathname + (s ? '#' + s : '')
    history.replaceState(null, '', url)
  }

  readHash()
  watch(selected, writeHash, { deep: true })

  const matches = (s, sel) => Object.entries(sel).every(([k, vals]) => {
    if (!vals.length) return true
    const v = s[k]
    return Array.isArray(v) ? v.some(x => vals.includes(x)) : vals.includes(v)
  })

  const results = computed(() => SPACES.filter(s => matches(s, selected)))

  /* Đếm kiểu facet */
  const counts = computed(() => {
    const out = {}
    FACETS.forEach(f => {
      out[f.id] = {}
      f.options.forEach(o => {
        const probe = {}
        Object.keys(selected).forEach(k => { probe[k] = selected[k] })
        probe[f.id] = selected[f.id].includes(o.id) ? selected[f.id] : selected[f.id].concat(o.id)
        out[f.id][o.id] = SPACES.filter(s => matches(s, probe)).length
      })
    })
    return out
  })

  const activeChips = computed(() =>
    Object.entries(selected).flatMap(([fid, vals]) => {
      const f = FACETS.find(x => x.id === fid)
      return vals.map(v => ({
        fid, vid: v, label: (f.options.find(o => o.id === v) || {}).label || v
      }))
    }))

  return {
    selected, results, counts, activeChips,
    toggle(fid, oid) {
      const a = selected[fid], i = a.indexOf(oid)
      if (i === -1) a.push(oid); else a.splice(i, 1)
    },
    clear(fid) { selected[fid] = [] },
    clearAll() { Object.keys(selected).forEach(k => { selected[k] = [] }) }
  }
}
