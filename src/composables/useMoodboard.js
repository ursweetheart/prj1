/* ═══════════════════════════════════════════════════════════════════════
 * Moodboard store — lưu không gian khách thích (localStorage)
 * ═══════════════════════════════════════════════════════════════════ */
import { reactive, computed } from 'vue'

const KEY = 'd3-moodboard-v1'
const saved = reactive({ ids: [] })

try {
  const raw = JSON.parse(localStorage.getItem(KEY) || '[]')
  if (Array.isArray(raw)) saved.ids = raw
} catch (e) { /* localStorage bị chặn */ }

function has(id) {
  return saved.ids.includes(id)
}

function toggle(id) {
  const i = saved.ids.indexOf(id)
  if (i === -1) saved.ids.push(id)
  else saved.ids.splice(i, 1)
  try { localStorage.setItem(KEY, JSON.stringify(saved.ids)) } catch (e) {}
}

const count = computed(() => saved.ids.length)

export function useMoodboard() {
  return { has, toggle, count }
}
