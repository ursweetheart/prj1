/* Bộ sưu tập (UC07, seq-13, act-8): the photos a visitor saved with the heart, each with a short note.
 *
 *   not signed in  ->  only in this browser (localStorage 'd3_bo_suu_tap'); nothing goes to the server
 *   signed in      ->  the account's collection on the server (same on every device)
 *   signing in while the browser holds photos  ->  merged into the account, then the browser copy is cleared
 *
 * Writes are optimistic: the heart reacts at once and is put back if the server refuses. */
import { reactive, watch } from 'vue'
import { STAFF, getMyCollection, hasRole, mergeCollection, removeFromCollection, saveToCollection, session, trackSave } from '@/api'

export const KEY = 'd3_bo_suu_tap'
export const MAX = 60
export const FULL_MESSAGE = 'Bộ sưu tập đã đủ 60 ảnh'

export const collection = reactive({ items: [], mode: 'local', ready: false, error: '' }) // items: [{ space_id, ghi_chu }]

function readLocal() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(v) ? v.filter(i => Number.isInteger(i?.space_id)).slice(0, MAX) : []
  } catch { return [] } // blocked storage or a broken value: start empty
}
function writeLocal() {
  try { localStorage.setItem(KEY, JSON.stringify(collection.items)) } catch { /* private mode: kept in memory only */ }
}
function clearLocal() {
  try { localStorage.removeItem(KEY) } catch { /* nothing to clear */ }
}
const fromServer = rows => rows.map(r => ({ space_id: r.space_id, ghi_chu: r.ghi_chu || '' }))

export const has = id => collection.items.some(i => i.space_id === id)
export const count = () => collection.items.length

async function persist(apply, undo, call) {
  collection.error = ''
  apply()
  if (collection.mode === 'local') { writeLocal(); return true }
  try { await call(); return true } catch (e) {
    undo()
    collection.error = e.status === 409 ? FULL_MESSAGE : 'Chưa lưu được, vui lòng thử lại.'
    return false
  }
}

export function add(id, ghiChu = '') {
  if (has(id)) return Promise.resolve(true)
  if (count() >= MAX) { collection.error = FULL_MESSAGE; return Promise.resolve(false) }
  const item = { space_id: id, ghi_chu: ghiChu }
  return persist(() => collection.items.push(item),
                 () => { collection.items = collection.items.filter(i => i.space_id !== id) }, // items holds a proxy, not `item`
                 () => saveToCollection(id, ghiChu))
    .then(ok => { if (ok && !hasRole(STAFF)) trackSave(id); return ok }) // staff saving is not demand
}

export function remove(id) {
  const at = collection.items.findIndex(i => i.space_id === id)
  if (at < 0) return Promise.resolve(true)
  const [item] = collection.items.slice(at, at + 1)
  return persist(() => collection.items.splice(at, 1),
                 () => collection.items.splice(at, 0, item),
                 () => removeFromCollection(id))
}

export const toggle = id => (has(id) ? remove(id) : add(id))

export function setNote(id, text) {
  const item = collection.items.find(i => i.space_id === id)
  const note = (text || '').trim().slice(0, 300)
  if (!item || item.ghi_chu === note) return Promise.resolve(true)
  const before = item.ghi_chu
  return persist(() => { item.ghi_chu = note }, () => { item.ghi_chu = before }, () => saveToCollection(id, note))
}

/* Follow the session: browser mode when signed out, account mode when signed in (merging the browser copy once). */
async function follow(userId) {
  collection.error = ''
  if (!userId) {
    collection.mode = 'local'
    collection.items = readLocal()
    collection.ready = true
    return
  }
  collection.mode = 'account'
  const local = readLocal()
  try {
    collection.items = fromServer(local.length ? await mergeCollection(local) : await getMyCollection())
    if (local.length) clearLocal() // only once the account has them
  } catch {
    collection.items = local // keep showing what the browser has; the next sign-in tries again
    collection.error = 'Chưa đồng bộ được bộ sưu tập với tài khoản.'
  }
  collection.ready = true
}

let started = false
export function startCollection() {
  if (started) return
  started = true
  watch(() => session.user?.id ?? null, follow, { immediate: true })
}
