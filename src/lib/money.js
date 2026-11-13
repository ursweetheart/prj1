/* VND for reading, same rules as backend/pipeline/estimate.py::vnd:
 * 478_800_000 -> "478,8 triệu", 1_250_000_000 -> "1,25 tỷ" (Vietnamese decimal comma, trailing zeros dropped) */
const num = (x, decimals) => x.toFixed(decimals).replace(/\.?0+$/, '').replace('.', ',')

export function formatVnd(amount) {
  if (amount >= 1e9) return num(amount / 1e9, 2) + ' tỷ'
  if (amount >= 1e6) return num(amount / 1e6, 1) + ' triệu'
  return Math.round(amount).toLocaleString('vi-VN') + ' đồng'
}
export const formatRange = r => formatVnd(r.min) + ' – ' + formatVnd(r.max)
