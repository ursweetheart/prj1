import { describe, expect, it } from 'vitest'
import { STUDIO, mailHref, mapHref, telHref, zaloHref } from './studio'

const real = gia_tri => ({ gia_tri, mau: false })

describe('studio contact links', () => {
  it('never links a sample value', () => {
    for (const f of [telHref, mailHref, zaloHref, mapHref]) {
      expect(f({ gia_tri: '0912 345 678', mau: true })).toBeNull()
      expect(f(null)).toBeNull()
      expect(f(real(''))).toBeNull()
    }
  })
  it('links confirmed values', () => {
    expect(telHref(real('0912 345 678'))).toBe('tel:0912345678')
    expect(telHref(real('+84 912 345 678'))).toBe('tel:+84912345678')
    expect(zaloHref(real('0912 345 678'))).toBe('https://zalo.me/0912345678')
    expect(mailHref(real('lienhe@d3studio.vn'))).toBe('mailto:lienhe@d3studio.vn')
    expect(mapHref(real('Số 5 Láng Hạ, Hà Nội')))
      .toBe('https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent('Số 5 Láng Hạ, Hà Nội'))
  })
  it('ships with every contact detail still marked as sample', () => {
    for (const k of ['dien_thoai', 'zalo', 'email', 'dia_chi', 'gio_lam']) expect(STUDIO[k].mau).toBe(true)
    expect(STUDIO.email.gia_tri.endsWith('.example')).toBe(true)
    expect(STUDIO.doi_ngu.map(p => p.ten)).toEqual(['Phạm Việt Tùng', 'Trần Xuân Bằng', 'Trần Xuân Tuấn'])
    expect(STUDIO.quy_trinh.buoc).toHaveLength(5)
  })
})
