/* review-tag-autocomplete: match what a reviewer types against a dimension's stored values.
   values: [{ ma_dinh_danh, ten, tu_dong_nghia, so_anh }] as GET /taxonomy returns them (so_anh only for staff). */

// Same folding as backend pipeline/taxonomy.fold: lower case, no accents, đ -> d. Spaces, '-' and '_' count as one space.
export const fold = s => String(s ?? '').toLowerCase().replace(/đ/g, 'd').normalize('NFD').replace(/\p{M}/gu, '')
  .replace(/[\s_-]+/g, ' ')

// backend pipeline/taxonomy.key: no separators at all, so "wabisabi" == "Wabi-sabi"
export const key = s => fold(s).replace(/ /g, '')

const words = v => [v.ma_dinh_danh, v.ten, ...(v.tu_dong_nghia || [])]

/** The value the text names exactly (code, name or synonym), or null. */
export const exact = (values, typed) => {
  const k = key(typed)
  return k ? values.find(v => words(v).some(w => key(w) === k)) || null : null
}

/** Matches best first: name starts with the text, then a synonym does, then the name contains it;
    within each group the value on more photos first. */
export function rank(values, typed, limit = 6) {
  const t = fold(typed).trimStart()
  if (!t) return []
  const group = v => {
    const name = fold(v.ten)
    if (name.startsWith(t)) return 0
    if ((v.tu_dong_nghia || []).some(s => fold(s).startsWith(t))) return 1
    return name.includes(t) ? 2 : -1
  }
  return values.map(v => ({ v, g: group(v) })).filter(x => x.g >= 0)
    .sort((a, b) => a.g - b.g || (b.v.so_anh || 0) - (a.v.so_anh || 0) || a.v.ten.localeCompare(b.v.ten, 'vi'))
    .slice(0, limit).map(x => x.v)
}

/** Grey completion after the typed text: the rest of the best match's name, only when the name itself starts with
    what was typed (folding keeps one character per character, so the typed length lines up with the name). */
export function completion(best, typed) {
  if (!best || !typed) return ''
  const t = fold(typed)
  return fold(best.ten).startsWith(t) && best.ten.length > typed.length ? best.ten.slice(typed.length) : ''
}
