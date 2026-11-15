/* Trắc nghiệm phong cách (UC06, seq-12): what the quiz page remembers between visits.
 *
 *   last result  ->  this browser (localStorage 'd3_trac_nghiem'): { cap, chon, ket_qua, at }
 *   saved result ->  the signed-in account (PUT /quiz/me re-scores the answers on the server)
 *   "Lưu kết quả" while signed out  ->  a pending flag; the answers are saved once, right after sign-in
 *
 * The server always does the scoring: only the pairs shown (cap) and the photos chosen (chon) are ever sent. */
import { effectScope, reactive, watch } from 'vue'
import { STAFF, getMyQuiz, hasRole, saveMyQuiz, session, trackQuizPick } from '@/api'

export const KEY = 'd3_trac_nghiem'
export const PENDING_KEY = 'd3_trac_nghiem_cho_luu'

export const quiz = reactive({ last: null, saved: null, status: '', error: '' }) // status: '' | 'saving' | 'saved'

const storage = {
  get(k) { try { return localStorage.getItem(k) } catch { return null } },
  set(k, v) { try { localStorage.setItem(k, v) } catch { /* private mode: kept in memory only */ } },
  drop(k) { try { localStorage.removeItem(k) } catch { /* nothing to drop */ } }
}

const valid = v => v && Array.isArray(v.cap) && Array.isArray(v.chon) && v.ket_qua && Array.isArray(v.ket_qua.phong_cach)

export function loadLast() {
  try {
    const v = JSON.parse(storage.get(KEY) || 'null')
    quiz.last = valid(v) ? v : null
  } catch { quiz.last = null } // a broken value: as if there were none
  return quiz.last
}

export function rememberLast(answers, ketQua) {
  quiz.last = { cap: answers.cap, chon: answers.chon, ket_qua: ketQua, at: new Date().toISOString() }
  quiz.status = ''
  storage.set(KEY, JSON.stringify(quiz.last))
}

/* A chosen photo is a behaviour signal (consent is checked in api.js); staff trying the quiz is not demand. */
export function trackPick(spaceId) {
  if (!hasRole(STAFF)) trackQuizPick(spaceId)
}

async function save(answers) {
  quiz.status = 'saving'; quiz.error = ''
  try {
    quiz.saved = await saveMyQuiz({ cap: answers.cap, chon: answers.chon })
    quiz.status = 'saved'
    return true
  } catch {
    quiz.status = ''
    quiz.error = 'Chưa lưu được kết quả, vui lòng thử lại.'
    return false
  }
}

/* "Lưu kết quả": saves now when signed in; otherwise remembers to save after sign-in and returns 'login'. */
export async function saveResult() {
  if (!quiz.last) return 'none'
  if (!session.user) { storage.set(PENDING_KEY, '1'); return 'login' }
  return (await save(quiz.last)) ? 'saved' : 'error'
}

async function follow(userId) {
  quiz.saved = null
  if (!userId) return
  if (storage.get(PENDING_KEY) && loadLast()) {
    storage.drop(PENDING_KEY) // once, even if it fails: the button is still there
    if (await save(quiz.last)) return
  }
  try { quiz.saved = await getMyQuiz() } catch { quiz.saved = null }
}

let started = false
export function startQuiz() {
  loadLast()
  if (started) return
  started = true
  // detached: started from the quiz page, but it must keep following the session after that page unmounts
  // (the visitor goes to /dang-nhap and the pending result is saved there)
  effectScope(true).run(() => watch(() => session.user?.id ?? null, follow, { immediate: true }))
}
