import { describe, expect, it } from 'vitest'
import { slug } from './slug'

describe('slug (same rule as taxonomy_admin.slug)', () => {
  it('drops accents and joins words', () => {
    expect(slug('Địa Trung Hải')).toBe('dia_trung_hai')
    expect(slug('  Bố cục & Công năng ')).toBe('bo_cuc_cong_nang')
    expect(slug('Ánh sáng')).toBe('anh_sang')
  })
  it('is empty without letters or digits, and at most 60 characters', () => {
    expect(slug('—!')).toBe('')
    expect(slug(null)).toBe('')
    expect(slug('a'.repeat(80))).toHaveLength(60)
  })
})
