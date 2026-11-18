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
  it('sends every file in one request and reports refused files (labelling-queue-feedback)', async () => {
    const { uploadAll } = await load()
    const sent = []
    vi.stubGlobal('fetch', vi.fn(async (url, { body }) => {
      expect(url).toContain('/spaces/ingest')
      sent.push([body.getAll('files').map(f => f.name), body.get('project')])
      return { ok: true, status: 202, json: async () => ({ tasks: [], refused: [{ name: 'b.pdf', ly_do: 'Chỉ nhận ảnh JPG, PNG hoặc WEBP.' }] }) }
    }))
    const files = ['a.jpg', 'b.pdf'].map(n => new File(['x'], n))
    const r = await uploadAll(files, 'Biệt thự')
    expect(sent).toEqual([[['a.jpg', 'b.pdf'], 'Biệt thự']])
    expect(r).toEqual({ total: 0, ok: 0, failed: [{ name: 'b.pdf', error: 'Chỉ nhận ảnh JPG, PNG hoặc WEBP.' }] })
  })
})

// labelling-queue-feedback: following the upload queue
import { pollTasks } from './api'

describe('pollTasks', () => {
  const tasks = [{ id: 1, relative_path: 'p/a.jpg' }, { id: 2, relative_path: 'p/b.jpg' }]
  it('polls until every task is done or failed and names the failures', async () => {
    const answers = [
      [{ id: 1, trang_thai: 'xong' }, { id: 2, trang_thai: 'dang_xu_ly' }],
      [{ id: 2, trang_thai: 'loi', loi: 'OSError: hỏng' }],
    ]
    const asked = [], seen = []
    const r = await pollTasks(tasks, async ids => { asked.push(ids); return answers.shift() }, (n, t) => seen.push([n, t]), async () => {})
    expect(asked).toEqual([[1, 2], [2]])
    expect(seen).toEqual([[0, 2], [1, 2], [2, 2]])
    expect(r).toEqual({ ok: 1, failed: [{ name: 'b.jpg', error: 'OSError: hỏng' }] })
  })
  it('retries a failed poll instead of giving up', async () => {
    let n = 0
    const r = await pollTasks(tasks.slice(0, 1), async () => { if (n++ === 0) throw new Error('net'); return [{ id: 1, trang_thai: 'xong' }] },
      () => {}, async () => {})
    expect(r.ok).toBe(1)
  })
})

// tracking-pipeline 6.2: a similar space opened from the list shown last (seq-2 b14)
describe('takeSimilarPick', () => {
  it('names the source space once, only for spaces in the list shown', async () => {
    const { getSimilar, takeSimilarPick } = await load()
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => [{ id: 30 }, { id: 31 }] })))
    await getSimilar(12)
    expect(takeSimilarPick(99)).toBe(null)
    expect(takeSimilarPick('30')).toBe(12)
    expect(takeSimilarPick(31)).toBe(null) // used once: the list is forgotten after a pick
  })
})

// publishing-workflow 5.2: optimised copies as a srcset
describe('imageSrcset', () => {
  it('lists the copies by width and ends with the original at its width', async () => {
    const { imageSrcset } = await load()
    const s = imageSrcset({ relative_path: 'p/a b.jpg', chieu_rong: 4000, kich_thuoc: { 960: '_kt/960/p/a b.jpg.webp', 480: '_kt/480/p/a b.jpg.webp' } })
    expect(s.split(', ').map(x => x.split(' ').pop())).toEqual(['480w', '960w', '4000w'])
    expect(s).toContain('/images/_kt/480/p/a%20b.jpg.webp 480w')
  })
  it('is empty without copies', async () => {
    const { imageSrcset } = await load()
    expect(imageSrcset({ relative_path: 'p/a.jpg' })).toBe('')
  })
})

// search-explanations 3.1: the API's object answer -> the list for callers, the rest in lastSearch
describe('search answers', () => {
  it('keeps returning the list and keeps the constraints and hint aside', async () => {
    const { searchSpaces, lastSearch, toCard } = await load()
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({
      ket_qua: [{ id: 1, relative_path: 'p/a.jpg', space_type: 'phong_khach', design_style: 'Japandi', ly_do: ['Gỗ tự nhiên'] }],
      rang_buoc: [{ chieu: 'khong_gian', ma: 'phong_khach', ten: 'Phòng khách' }], goi_y: null }) })))
    const rows = await searchSpaces('phòng khách gỗ')
    expect(rows.map(r => r.id)).toEqual([1])
    expect(lastSearch.rang_buoc[0].ten).toBe('Phòng khách')
    expect(toCard(rows[0]).why).toEqual(['Gỗ tự nhiên'])
  })
})

// search-explanations 2.2: project filter query
describe('projectFilterParams', () => {
  it('repeats a dimension for several values and leaves defaults out', async () => {
    const { projectFilterParams } = await load()
    const pairs = projectFilterParams({ phong_cach: ['Japandi', 'Indochine'], loai_cong_trinh: ['can_ho'] }, [60, ''], 'xem_nhieu')
    expect(new URLSearchParams(pairs).toString())
      .toBe('phong_cach=Japandi&phong_cach=Indochine&loai_cong_trinh=can_ho&dien_tich_tu=60&sap_xep=xem_nhieu')
    expect(projectFilterParams({}, [], 'moi_nhat')).toEqual([])
  })
})
