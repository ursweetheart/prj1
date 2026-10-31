import { afterEach, describe, expect, it, vi } from 'vitest'

async function load(fetchImpl) {
  vi.resetModules() // the list is cached per module instance
  vi.stubGlobal('localStorage', { getItem: () => null, setItem() {}, removeItem() {} })
  vi.stubGlobal('fetch', vi.fn(fetchImpl))
  const { usePortfolio } = await import('./usePortfolio.js')
  const state = usePortfolio()
  await vi.waitFor(() => expect(state.source).not.toBe('loading'))
  return state
}

afterEach(() => vi.unstubAllGlobals())

describe('usePortfolio', () => {
  it('shows the published spaces and the customer-facing taxonomy from the API', async () => {
    const row = { id: 9, relative_path: 'luxury/a.jpg', space_type: 'phong_khach', design_style: 'Luxury',
                  brightness: 'dark', temperature: 'warm', tags: { vat_lieu: ['go', 'da_tu_nhien'] } }
    const dims = [
      { ma_dinh_danh: 'vat_lieu', ten: 'Vật liệu', hien_thi_cho_khach: true, values: [{ ma_dinh_danh: 'go', ten: 'Gỗ' }] },
      { ma_dinh_danh: 'noi_bo', ten: 'Nội bộ', hien_thi_cho_khach: false, values: [] }
    ]
    const state = await load(async url => {
      if (url.includes('/taxonomy')) return { ok: true, status: 200, json: async () => dims }
      expect(url).toContain('review_status=published')
      return { ok: true, status: 200, json: async () => [row] }
    })
    expect(state.source).toBe('api')
    expect(state.spaces).toHaveLength(1)
    expect(state.spaces[0]).toMatchObject({ apiId: 9, khonggian: 'phong-khach', phongcach: 'luxury', tongmau: ['toi', 'am'],
                                            tags: { vat_lieu: ['go', 'da_tu_nhien'] } })
    expect(state.facets).toEqual([{ id: 'vat_lieu', label: 'Vật liệu', options: [{ id: 'go', label: 'Gỗ' }] }])
  })

  it('an empty API answer is real data, not a reason to show the demo', async () => {
    const state = await load(async () => ({ ok: true, status: 200, json: async () => [] }))
    expect(state.source).toBe('api')
    expect(state.spaces).toEqual([])
  })

  it('falls back to the demo data when the API cannot be reached (static site)', async () => {
    const state = await load(async () => ({ ok: false, status: 404, json: async () => ({}) }))
    expect(state.source).toBe('demo')
    expect(state.spaces.length).toBeGreaterThan(0)
  })
})
