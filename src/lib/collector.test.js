import { describe, expect, it } from 'vitest'
import { batchBody, createCollector, deviceType, EVERY_MS, MAX_AGE_MS, trafficSource } from './collector'

describe('trafficSource', () => {
  it('names a campaign from utm_source first', () => {
    expect(trafficSource('https://www.google.com/', '?utm_source=Facebook-Ads', 'd3.vn')).toBe('facebook_ads')
  })
  it('classifies the referrer', () => {
    expect(trafficSource('', '', 'd3.vn')).toBe('truc_tiep')
    expect(trafficSource('https://d3.vn/du-an', '', 'd3.vn')).toBe('truc_tiep')
    expect(trafficSource('https://www.google.com.vn/', '', 'd3.vn')).toBe('tim_kiem')
    expect(trafficSource('https://coccoc.com/search', '', 'd3.vn')).toBe('tim_kiem')
    expect(trafficSource('https://l.facebook.com/', '', 'd3.vn')).toBe('mang_xa_hoi')
    expect(trafficSource('https://zalo.me/x', '', 'd3.vn')).toBe('mang_xa_hoi')
    expect(trafficSource('https://kenh14.vn/bai', '', 'd3.vn')).toBe('gioi_thieu')
  })
})

describe('deviceType', () => {
  it('uses width and a coarse pointer', () => {
    expect(deviceType(390, true)).toBe('di_dong')
    expect(deviceType(820, true)).toBe('may_tinh_bang')
    expect(deviceType(390, false)).toBe('may_tinh') // a narrow desktop window is still a computer
    expect(deviceType(1440, false)).toBe('may_tinh')
  })
})

describe('batchBody', () => {
  const events = [{ loai: 'luu_anh', fields: { space_id: 7 }, at: 1000 }, { loai: 'xem_trang', fields: { trang: '/' }, at: 3000 }]
  it('sends details and event times only with consent', () => {
    const ctx = { consented: true, phien_id: 'p'.repeat(32), ma_thiet_bi: 'd'.repeat(32), nguon: 'tim_kiem', thiet_bi: 'di_dong', ca_nhan_hoa: true }
    expect(batchBody(events, 5000, ctx)).toEqual({ dong_y: true, phien_id: ctx.phien_id, ma_thiet_bi: ctx.ma_thiet_bi, nguon: 'tim_kiem',
      thiet_bi: 'di_dong', ca_nhan_hoa: true, su_kien: [{ space_id: 7, loai: 'luu_anh', cach_ms: 4000 }, { trang: '/', loai: 'xem_trang', cach_ms: 2000 }] })
    expect(batchBody(events, 5000, { consented: false })).toEqual({ dong_y: false, su_kien: [{ loai: 'luu_anh' }, { loai: 'xem_trang' }] })
  })
  it('caps the age the server accepts', () => {
    expect(batchBody(events.slice(0, 1), 1000 + MAX_AGE_MS + 5, { consented: true }).su_kien[0].cach_ms).toBe(MAX_AGE_MS)
  })
})

describe('createCollector', () => {
  const make = () => {
    const sent = [], timers = []
    let t = 0
    const c = createCollector({ send: b => sent.push(b), context: () => ({ consented: false }), now: () => t,
      schedule: (fn, ms) => { timers.push({ fn, ms }); return timers.length }, cancel: () => {} })
    return { c, sent, timers, tick: ms => { t += ms } }
  }
  it('sends one batch 5 s after the first event', () => {
    const { c, sent, timers } = make()
    c.push('luu_anh'); c.push('ap_dung_bo_loc'); c.push('bam_CTA')
    expect(timers).toHaveLength(1)
    expect(timers[0].ms).toBe(EVERY_MS)
    timers[0].fn()
    expect(sent).toHaveLength(1)
    expect(sent[0].su_kien.map(e => e.loai)).toEqual(['luu_anh', 'ap_dung_bo_loc', 'bam_CTA'])
  })
  it('flushes at once on page leave and splits big buffers', () => {
    const { c, sent } = make()
    for (let i = 0; i < 120; i++) c.push('xem_trang')
    c.flush()
    expect(sent.map(b => b.su_kien.length)).toEqual([50, 50, 20])
    c.flush()
    expect(sent).toHaveLength(3) // nothing waiting: nothing sent
  })
})
