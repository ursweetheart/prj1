import { describe, expect, it } from 'vitest'
import { completion, exact, fold, key, rank } from './tagMatch'

const V = [
  { ma_dinh_danh: 'Japandi', ten: 'Japandi', tu_dong_nghia: [], so_anh: 12 },
  { ma_dinh_danh: 'Hien_dai', ten: 'Hiện đại', tu_dong_nghia: ['hien dai', 'modern'], so_anh: 30 },
  { ma_dinh_danh: 'Tan_co_dien', ten: 'Tân cổ điển', tu_dong_nghia: ['neo classic'], so_anh: 41 },
  { ma_dinh_danh: 'Toi_gian', ten: 'Tối giản', tu_dong_nghia: ['minimalism'], so_anh: 23 },
  { ma_dinh_danh: 'Dien_vien', ten: 'Điền viên', tu_dong_nghia: [], so_anh: 1 },
  { ma_dinh_danh: 'Wabi_sabi', ten: 'Wabi-sabi', tu_dong_nghia: ['wabi sabi'], so_anh: 5 },
]
const names = list => list.map(v => v.ten)

describe('fold and key', () => {
  it('drops accents and case, đ -> d, separators alike', () => {
    expect(fold('Điền_viên-Hiện  đại')).toBe('dien vien hien dai')
    expect(key('Wabi-sabi')).toBe(key('wabisabi'))
  })
})

describe('rank', () => {
  it('"Ja" puts Japandi first', () => expect(names(rank(V, 'Ja'))[0]).toBe('Japandi'))
  it('accents and synonyms', () => {
    expect(names(rank(V, 'hien'))).toEqual(['Hiện đại'])
    expect(names(rank(V, 'modern'))).toEqual(['Hiện đại'])
  })
  it('several prefix matches: more photos first', () => expect(names(rank(V, 't'))).toEqual(['Tân cổ điển', 'Tối giản']))
  it('name prefix before name contains', () => expect(names(rank(V, 'dien'))).toEqual(['Điền viên', 'Tân cổ điển']))
  it('synonym prefix', () => {
    expect(names(rank(V, 'neo'))).toEqual(['Tân cổ điển']) // only via its synonym "neo classic"
  })
  it('synonym prefix before name contains', () => {
    const W = [{ ma_dinh_danh: 'A', ten: 'Mặt tiền', tu_dong_nghia: [], so_anh: 99 },
      { ma_dinh_danh: 'B', ten: 'Tân', tu_dong_nghia: ['tien nghi'], so_anh: 1 }]
    expect(names(rank(W, 'tien'))).toEqual(['Tân', 'Mặt tiền'])
  })
  it('nothing matches', () => expect(rank(V, 'xyz')).toEqual([]))
  it('caps the list', () => expect(rank(V, 'i', 2)).toHaveLength(2))
})

describe('exact', () => {
  it('code, name or synonym, any case or accents', () => {
    expect(exact(V, 'hiện đại').ma_dinh_danh).toBe('Hien_dai')
    expect(exact(V, 'MODERN').ma_dinh_danh).toBe('Hien_dai')
    expect(exact(V, 'wabisabi').ma_dinh_danh).toBe('Wabi_sabi')
    expect(exact(V, 'Mid-century')).toBeNull()
    expect(exact(V, '  ')).toBeNull()
  })
})

describe('completion', () => {
  it('the rest of the name after the typed text', () => {
    expect(completion(V[0], 'Ja')).toBe('pandi')
    expect(completion(V[1], 'hien')).toBe(' đại')
  })
  it('none when the match came from a synonym or is complete', () => {
    expect(completion(V[1], 'mod')).toBe('')
    expect(completion(V[0], 'Japandi')).toBe('')
  })
})
