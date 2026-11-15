import { describe, expect, it } from 'vitest'
import { ctaTarget, objectOf, routePattern, scrollFraction } from './pageTracking'
import { filterValues } from '@/composables/useBrowse'

const r = path => ({ matched: [{ path }], path: '/x' })

describe('page tracking', () => {
  it('stores route patterns, never real paths', () => {
    expect(routePattern(r('/du-an/:slug'))).toBe('/du-an/:slug')
    expect(routePattern(r('/khong-gian/:id(\\d+)'))).toBe('/khong-gian/:id')
    expect(routePattern(r('/bo-suu-tap/xem/:ma'))).toBe('/bo-suu-tap/xem/:ma')
    expect(routePattern({ matched: [], path: '/' })).toBe('/')
  })
  it('keeps only a project slug or a photo id as the object', () => {
    expect(objectOf('/du-an/:slug', { slug: 'beaumont-lounge' })).toBe('beaumont-lounge')
    expect(objectOf('/khong-gian/:id', { id: '42' })).toBe('42')
    expect(objectOf('/bo-suu-tap/xem/:ma', { ma: 'ABC123' })).toBeNull()
    expect(objectOf('/du-an/:slug', { slug: 'Bad Slug' })).toBeNull()
  })
  it('recognises CTA links with or without the base', () => {
    const o = 'http://localhost:8080'
    expect(ctaTarget('/prj1/lien-he', o, '/prj1/')).toBe('/lien-he')
    expect(ctaTarget('/prj1/uoc-tinh/', o, '/prj1/')).toBe('/uoc-tinh')
    expect(ctaTarget('/lien-he#zalo', o, '/')).toBe('/lien-he')
    expect(ctaTarget('/prj1/du-an', o, '/prj1/')).toBeNull()
    expect(ctaTarget('https://zalo.me/1', o, '/prj1/')).toBeNull()
  })
  it('measures scroll depth', () => {
    expect(scrollFraction(0, 800, 3200)).toBe(0.25)
    expect(scrollFraction(2400, 800, 3200)).toBe(1)
    expect(scrollFraction(0, 800, 600)).toBe(1)
  })
  it('turns a filter choice into stable, valid values', () => {
    expect(filterValues({ phong_cach: ['Japandi', 'Indochine'], khong_gian: [], 'bad-dim': ['x'] }))
      .toEqual(['phong_cach:Indochine', 'phong_cach:Japandi'])
    expect(filterValues({})).toEqual([])
  })
})
