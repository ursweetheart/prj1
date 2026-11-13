import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// lib/collection.js against a fake API module: what goes to the browser, what goes to the server, and when
let mem, api
async function load(stored) {
  vi.resetModules()
  mem = stored ? { d3_bo_suu_tap: typeof stored === 'string' ? stored : JSON.stringify(stored) } : {}
  vi.stubGlobal('localStorage', {
    getItem: k => mem[k] ?? null, setItem: (k, v) => { mem[k] = v }, removeItem: k => { delete mem[k] }
  })
  const { reactive } = await import('vue')
  api = {
    session: reactive({ token: null, user: null }),
    getMyCollection: vi.fn(async () => [{ space_id: 9, ghi_chu: 'từ máy khác' }]),
    mergeCollection: vi.fn(async items => items.map(i => ({ ...i }))),
    saveToCollection: vi.fn(async () => []),
    removeFromCollection: vi.fn(async () => null),
    trackSave: vi.fn(),
    hasRole: vi.fn(() => false),
    STAFF: ['architect', 'lead_architect', 'admin']
  }
  vi.doMock('@/api', () => api)
  const m = await import('./collection.js')
  m.startCollection()
  return m
}
const settle = async () => { await nextTick(); await Promise.resolve(); await Promise.resolve(); await nextTick() }

afterEach(() => { vi.unstubAllGlobals(); vi.doUnmock('@/api') })

describe('without an account', () => {
  it('toggles and keeps notes in the browser only', async () => {
    const m = await load()
    await m.toggle(21); await m.toggle(22); await m.setNote(21, '  thích màu gỗ ')
    expect(JSON.parse(mem.d3_bo_suu_tap)).toEqual([{ space_id: 21, ghi_chu: 'thích màu gỗ' }, { space_id: 22, ghi_chu: '' }])
    await m.toggle(22)
    expect(m.has(22)).toBe(false)
    expect(api.saveToCollection).not.toHaveBeenCalled()
    expect(api.removeFromCollection).not.toHaveBeenCalled()
  })

  it('stops at 60 with a message', async () => {
    const m = await load(Array.from({ length: 60 }, (_, i) => ({ space_id: i + 1, ghi_chu: '' })))
    expect(await m.add(99)).toBe(false)
    expect(m.collection.error).toBe('Bộ sưu tập đã đủ 60 ảnh')
    expect(m.count()).toBe(60)
  })

  it('survives a broken stored value', async () => {
    const m = await load('{oops')
    expect(m.count()).toBe(0)
    await m.add(5)
    expect(JSON.parse(mem.d3_bo_suu_tap)).toEqual([{ space_id: 5, ghi_chu: '' }])
  })
})

describe('save events (trend-dashboard)', () => {
  it('a successful add sends one save event, a remove sends none', async () => {
    const m = await load()
    await m.add(21)
    expect(api.trackSave).toHaveBeenCalledTimes(1)
    expect(api.trackSave).toHaveBeenCalledWith(21)
    await m.remove(21)
    expect(api.trackSave).toHaveBeenCalledTimes(1)
  })

  it('no event when the add fails or the user is staff', async () => {
    const m = await load(Array.from({ length: 60 }, (_, i) => ({ space_id: i + 1, ghi_chu: '' })))
    await m.add(99)
    expect(api.trackSave).not.toHaveBeenCalled()
    const m2 = await load()
    api.hasRole.mockReturnValue(true)
    await m2.add(5)
    expect(api.trackSave).not.toHaveBeenCalled()
  })
})

describe('signing in', () => {
  it('merges the browser photos once, then clears the browser copy', async () => {
    const m = await load([{ space_id: 21, ghi_chu: 'thích màu gỗ' }, { space_id: 22, ghi_chu: '' }])
    api.session.user = { id: 7 }
    await settle()
    expect(api.mergeCollection).toHaveBeenCalledTimes(1)
    expect(api.mergeCollection).toHaveBeenCalledWith([{ space_id: 21, ghi_chu: 'thích màu gỗ' }, { space_id: 22, ghi_chu: '' }])
    expect(mem.d3_bo_suu_tap).toBeUndefined()
    expect(m.collection.mode).toBe('account')
    expect(m.collection.items.map(i => i.space_id)).toEqual([21, 22])
  })

  it('loads the account collection when the browser holds nothing', async () => {
    const m = await load()
    api.session.user = { id: 7 }
    await settle()
    expect(api.mergeCollection).not.toHaveBeenCalled()
    expect(m.collection.items).toEqual([{ space_id: 9, ghi_chu: 'từ máy khác' }])
  })

  it('writes to the account and puts the heart back when the server refuses', async () => {
    const m = await load()
    api.session.user = { id: 7 }
    await settle()
    api.saveToCollection.mockRejectedValueOnce(Object.assign(new Error('full'), { status: 409 }))
    expect(await m.add(30)).toBe(false)
    expect(m.has(30)).toBe(false)
    expect(m.collection.error).toBe('Bộ sưu tập đã đủ 60 ảnh')
    expect(mem.d3_bo_suu_tap).toBeUndefined() // account mode never writes the browser copy
  })

  it('signing out shows the (empty) browser collection again', async () => {
    const m = await load([{ space_id: 21, ghi_chu: '' }])
    api.session.user = { id: 7 }
    await settle()
    api.session.user = null
    await settle()
    expect(m.collection.mode).toBe('local')
    expect(m.count()).toBe(0)
  })
})
