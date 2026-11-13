import { afterEach, describe, expect, it, vi } from 'vitest'

const ok = data => ({ ok: true, status: 200, json: async () => data })

async function load(fetchImpl) {
  vi.resetModules() // probe and cache live per module instance
  vi.stubGlobal('localStorage', { getItem: () => null, setItem() {}, removeItem() {} })
  vi.stubGlobal('fetch', vi.fn(fetchImpl))
  return import('./projectSpaces.js')
}

afterEach(() => vi.unstubAllGlobals())

describe('slug <-> folder', () => {
  it('maps both ways and builds the project photo link', async () => {
    const m = await load(async () => ok([]))
    expect(m.folderOf('beaumont-lounge')).toBe('beaumont_lounge')
    expect(m.slugOf('beaumont_lounge/03.jpg')).toBe('beaumont-lounge')
    expect(m.fileOf('beaumont_lounge/03.jpg')).toBe('03.jpg')
    expect(m.projectPhotoHref('apartment_in_grey/01.jpg')).toBe('/du-an/apartment-in-grey?anh=01.jpg')
  })
})

describe('loadProjectSpaces', () => {
  it('returns published spaces by file name when the backend answers', async () => {
    const m = await load(async url => {
      if (url.includes('/taxonomy')) return ok([])
      expect(url).toContain('/projects/beaumont_lounge/spaces')
      return ok([{ id: 7, relative_path: 'beaumont_lounge/03.jpg' }])
    })
    const spaces = await m.loadProjectSpaces('beaumont-lounge')
    expect(spaces.get('03.jpg').id).toBe(7)
    expect(m.ai.state).toBe('on')
  })

  it('is null and turns AI off when the backend is missing, without asking for the project', async () => {
    const calls = []
    const m = await load(async url => { calls.push(url); return { ok: false, status: 404, json: async () => ({}) } })
    expect(await m.loadProjectSpaces('beaumont-lounge')).toBeNull()
    expect(m.ai.state).toBe('off')
    expect(calls.every(u => u.includes('/taxonomy'))).toBe(true)
  })

  it('is null when fetch itself fails', async () => {
    const m = await load(async () => { throw new TypeError('network') })
    expect(await m.loadProjectSpaces('x')).toBeNull()
  })
})

describe('pending photo', () => {
  it('is taken once', async () => {
    const m = await load(async () => ok([]))
    const f = { name: 'a.jpg' }
    m.setPendingPhoto(f)
    expect(m.takePendingPhoto()).toBe(f)
    expect(m.takePendingPhoto()).toBeNull()
  })
})
