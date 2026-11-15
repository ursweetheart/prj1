import { describe, expect, it } from 'vitest'
import { needsPriceApproval } from './priceRule'

describe('needsPriceApproval (same cases as the backend test)', () => {
  it.each([
    ['Phí thiết kế 250.000 đ/m²', true], ['Biệt thự khoảng 1,5 tỷ', true], ['Gói từ 300 triệu', true], ['chỉ 45tr', true],
    ['Đơn giá 3.500.000 VND', true], ['Thiết kế mất 3 đến 4 tuần', false], ['Bảo hành 24 tháng', false], ['Quy trình 5 bước', false]
  ])('%s -> %s', (text, flag) => expect(needsPriceApproval('faq', text)).toBe(flag))
  it('a price entry always needs approval', () => expect(needsPriceApproval('price', 'không có số')).toBe(true))
})
