import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// lib/quiz.js against a fake API module: the browser copy, saving after sign-in, and pick events
let mem, api
const ANSWERS = { cap: [[1, 2], [3, 4]], chon: [1, 3] }
const RESULT = { phong_cach: [{ ma: 'Japandi', ten: 'Japandi', ti_le: 100 }], goi_y: [] }

async function load(stored, { broken = false } = {}) {
  vi.resetModules()
  mem = stored || {}
  vi.stubGlobal('localStorage', broken
    ? { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') }, removeItem: () => { throw new Error('blocked') } }
    : { getItem: k => mem[k] ?? null, setItem: (k, v) => { mem[k] = v }, removeItem: k => { delete mem[k] } })
  const { reactive } = await import('vue')
  api = {
    session: reactive({ token: null, user: null }),
    getMyQuiz: vi.fn(async () => null),
    saveMyQuiz: vi.fn(async a => ({ ...RESULT, luu_luc: 'now', sent: a })),
    trackQuizPick: vi.fn(),
    hasRole: vi.fn(() => false),
    STAFF: ['architect', 'lead_architect', 'admin']
  }
  vi.doMock('@/api', () => api)
  const m = await import('./quiz.js')
  m.startQuiz()
  return m
}
const settle = async () => { for (let i = 0; i < 4; i++) { await nextTick(); await Promise.resolve() } }

afterEach(() => { vi.unstubAllGlobals(); vi.doUnmock('@/api') })

describe('last result in the browser', () => {
  it('is stored and read back', async () => {
    let m = await load()
    m.rememberLast(ANSWERS, RESULT)
    const kept = mem.d3_trac_nghiem
    m = await load({ d3_trac_nghiem: kept })
    expect(m.quiz.last.ket_qua).toEqual(RESULT)
    expect(m.quiz.last.chon).toEqual([1, 3])
  })

  it('tolerates a broken value and blocked storage', async () => {
    let m = await load({ d3_trac_nghiem: '{oops' })
    expect(m.quiz.last).toBe(null)
    m = await load(null, { broken: true })
    expect(() => m.rememberLast(ANSWERS, RESULT)).not.toThrow()
    expect(m.quiz.last.ket_qua).toEqual(RESULT) // kept in memory
  })
})

describe('saving to the account', () => {
  it('asks to sign in, then saves once right after sign-in', async () => {
    const m = await load()
    m.rememberLast(ANSWERS, RESULT)
    expect(await m.saveResult()).toBe('login')
    expect(api.saveMyQuiz).not.toHaveBeenCalled()
    api.session.user = { id: 7, role: 'visitor' }
    await settle()
    expect(api.saveMyQuiz).toHaveBeenCalledTimes(1)
    expect(api.saveMyQuiz).toHaveBeenCalledWith({ cap: ANSWERS.cap, chon: ANSWERS.chon }) // never scores
    expect(m.quiz.status).toBe('saved')
    expect(mem.d3_trac_nghiem_cho_luu).toBeUndefined()
    api.session.user = null; await settle()
    api.session.user = { id: 7, role: 'visitor' }; await settle()
    expect(api.saveMyQuiz).toHaveBeenCalledTimes(1) // the flag was cleared
    expect(api.getMyQuiz).toHaveBeenCalled()
  })

  it('saves directly when signed in', async () => {
    const m = await load()
    api.session.user = { id: 7, role: 'visitor' }; await settle()
    m.rememberLast(ANSWERS, RESULT)
    expect(await m.saveResult()).toBe('saved')
    expect(m.quiz.saved.phong_cach[0].ma).toBe('Japandi')
  })
})

describe('pick events', () => {
  it('are sent for visitors and skipped for staff', async () => {
    const m = await load()
    m.trackPick(5)
    expect(api.trackQuizPick).toHaveBeenCalledWith(5)
    api.hasRole.mockReturnValue(true)
    m.trackPick(6)
    expect(api.trackQuizPick).toHaveBeenCalledTimes(1)
  })
})
