import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// api.js reads localStorage / location at import time or on call, so stub them and import fresh each test
const jwt = exp => 'h.' + btoa(JSON.stringify({ sub: '1', exp })).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') + '.s' // real JWTs are base64url, no padding
const inSeconds = s => Math.floor(Date.now() / 1000) + s

let mem
async function load(hash = '') {
  vi.resetModules()
  mem = {}
  vi.stubGlobal('localStorage', {
    getItem: k => mem[k] ?? null, setItem: (k, v) => { mem[k] = v }, removeItem: k => { delete mem[k] }
  })
  vi.stubGlobal('location', { hash, pathname: '/prj1/', search: '' })
  vi.stubGlobal('history', { replaceState: vi.fn((_s, _t, url) => { location.hash = url.includes('#') ? '#' + url.split('#')[1] : '' }) })
  return import('./api.js')
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe('tokenExpiry', () => {
  it('reads exp from the JWT payload, 0 when unreadable', async () => {
    const { tokenExpiry } = await load()
    expect(tokenExpiry(jwt(1_000))).toBe(1_000_000)
    expect(tokenExpiry('garbage')).toBe(0)
  })
})

describe('OAuth return', () => {
  it('keeps the token from #token=... and removes it from the address bar', async () => {
    const t = jwt(inSeconds(3600))
    const { adoptTokenFromHash, session } = await load('#token=' + t)
    adoptTokenFromHash()
    expect(session.token).toBe(t)
    expect(mem.d3_token).toBe(t)
    expect(location.hash).toBe('')
  })

  it('ignores any other hash', async () => {
    const { adoptTokenFromHash, session } = await load('#section-2')
    adoptTokenFromHash()
    expect(session.token).toBeNull()
  })
})

describe('roles', () => {
  it('hasRole is false when signed out and checks the role otherwise', async () => {
    const { hasRole, session, STAFF } = await load()
    expect(hasRole(STAFF)).toBe(false)
    session.user = { role: 'sales' }
    expect(hasRole(STAFF)).toBe(false)
    session.user = { role: 'architect' }
    expect(hasRole(STAFF)).toBe(true)
  })
})

describe('sliding session', () => {
  it('swaps the token for a fresh one shortly before it expires', async () => {
    const fresh = jwt(inSeconds(7200))
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ access_token: fresh }) })
    vi.stubGlobal('fetch', fetchMock)
    const { adoptTokenFromHash, session } = await load('#token=' + jwt(inSeconds(6 * 60))) // expires in 6 min
    adoptTokenFromHash()
    expect(fetchMock).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(61_000) // 5 min before expiry
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/refresh')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(session.token).toBe(fresh)
  })

  it('signs the user out when the server rejects the token', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'invalid or expired token' }) }))
    const { adoptTokenFromHash, session } = await load('#token=' + jwt(inSeconds(60)))
    adoptTokenFromHash()
    await vi.advanceTimersByTimeAsync(1)
    expect(session.token).toBeNull()
    expect(mem.d3_token).toBeUndefined()
  })
})

describe('uploadAll', () => {
  it('sends one file at a time in order, keeps going after a failure and reports it', async () => {
    const { uploadAll } = await load()
    let inFlight = 0
    const sent = []
    vi.stubGlobal('fetch', vi.fn(async (url, { body }) => {
      expect(url).toContain('/spaces/ingest')
      expect(++inFlight).toBe(1) // never two at once: single GPU
      const name = body.get('file').name
      sent.push([name, body.get('project')])
      await Promise.resolve()
      inFlight--
      return name === 'b.jpg'
        ? { ok: false, status: 415, json: async () => ({ detail: 'image only (jpg/png/webp)' }) }
        : { ok: true, status: 201, json: async () => ({}) }
    }))
    const files = ['a.jpg', 'b.jpg', 'c.jpg'].map(n => new File(['x'], n))
    const progress = []
    const failed = await uploadAll(files, 'Biệt thự', n => progress.push(n))
    expect(sent).toEqual([['a.jpg', 'Biệt thự'], ['b.jpg', 'Biệt thự'], ['c.jpg', 'Biệt thự']])
    expect(progress).toEqual([1, 2, 3])
    expect(failed).toEqual([{ name: 'b.jpg', error: 'image only (jpg/png/webp)' }])
  })
})
