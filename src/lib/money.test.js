import { describe, expect, it } from 'vitest'
import { formatRange, formatVnd } from './money.js'

describe('formatVnd (same cases as the Python formatter)', () => {
  it('millions with one decimal, billions with two, no trailing zeros', () => {
    expect(formatVnd(478_800_000)).toBe('478,8 triệu')
    expect(formatVnd(770_000_000)).toBe('770 triệu')
    expect(formatVnd(1_250_000_000)).toBe('1,25 tỷ')
    expect(formatVnd(2_000_000_000)).toBe('2 tỷ')
    expect(formatRange({ min: 478_800_000, max: 770_000_000 })).toBe('478,8 triệu – 770 triệu')
  })
})
