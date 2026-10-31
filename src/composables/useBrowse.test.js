import { describe, expect, it, vi } from 'vitest'
import { useBrowse } from './useBrowse.js'

vi.stubGlobal('location', { hash: '', pathname: '/cong-trinh' })
vi.stubGlobal('history', { replaceState() {} })

const facets = [
  { id: 'phong_cach', label: 'Phong cách', options: [{ id: 'Luxury', label: 'Luxury' }, { id: 'Japandi', label: 'Japandi' }] },
  { id: 'vat_lieu', label: 'Vật liệu', options: [{ id: 'go', label: 'Gỗ' }, { id: 'kinh', label: 'Kính' }] }
]
const spaces = [
  { id: 1, tags: { phong_cach: ['Luxury'], vat_lieu: ['go', 'kinh'] } },
  { id: 2, tags: { phong_cach: ['Japandi'], vat_lieu: ['go'] } },
  { id: 3, tags: { phong_cach: ['Luxury'] } }
]

describe('useBrowse', () => {
  it('ANDs across dimensions, ORs within one, and counts what each option would add', () => {
    const b = useBrowse(() => spaces, () => facets)
    b.toggle('vat_lieu', 'go')
    expect(b.results.value.map(s => s.id)).toEqual([1, 2])
    expect(b.counts.value.phong_cach).toEqual({ Luxury: 1, Japandi: 1 })
    expect(b.counts.value.vat_lieu).toEqual({ go: 2, kinh: 2 }) // go OR kinh -> spaces 1, 2

    b.toggle('phong_cach', 'Luxury')
    expect(b.results.value.map(s => s.id)).toEqual([1])
    expect(b.activeChips.value.map(c => c.label)).toEqual(['Luxury', 'Gỗ'])

    b.clearAll()
    expect(b.results.value).toHaveLength(3)
  })

  it('ignores a hash key that is not a known dimension', () => {
    location.hash = '#bogus=x&vat_lieu=kinh'
    const b = useBrowse(() => spaces, () => facets)
    expect(b.results.value.map(s => s.id)).toEqual([1])
    location.hash = ''
  })
})
