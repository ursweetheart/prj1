/* Client for the D3 Studio AI API (FastAPI, see api.py at the repo root). */

const SPACE_VI = {
  phong_khach: 'Phòng khách', phong_ngu_master: 'Phòng ngủ master', phong_ngu_phu: 'Phòng ngủ phụ',
  bep_va_an: 'Bếp & phòng ăn', phong_lam_viec: 'Phòng làm việc', sanh_thong_tang: 'Sảnh',
  ban_cong: 'Ban công', phong_tam: 'Phòng tắm', lounge_thuong_mai: 'Lounge', khac: 'Không gian'
}
// DB values -> facet ids used by the prototype's labels in data/index.js
const KG = {
  phong_khach: 'phong-khach', phong_ngu_master: 'phong-ngu', phong_ngu_phu: 'phong-ngu',
  bep_va_an: 'bep', lounge_thuong_mai: 'quay-bar', sanh_thong_tang: 'sanh'
}
const PC = {
  Indochine: 'indochine', Japandi: 'japandi', Wabi_sabi: 'wabi-sabi', Hien_dai: 'hien-dai',
  Tan_co_dien: 'tan-co-dien', Luxury: 'luxury', Toi_gian: 'toi-gian', Scandinavian: 'scandi'
}

async function get(path, params) {
  const qs = params ? '?' + new URLSearchParams(params) : ''
  const res = await fetch('/api' + path + qs)
  if (!res.ok) throw new Error(res.status === 404 ? 'Không tìm thấy không gian này.' : 'Máy chủ AI không phản hồi (' + res.status + ').')
  return res.json()
}

export const imageUrl = path => '/images/' + encodeURI(path)
export const spaceLabel = type => SPACE_VI[type] || 'Không gian'

/* API row -> shape SpaceCard expects */
export const toCard = r => ({
  id: 'ai-' + r.id,
  apiId: r.id,
  projectName: r.relative_path.split('/')[0].replace(/_/g, ' '),
  space: spaceLabel(r.space_type),
  img: imageUrl(r.relative_path),
  ratio: 'sq',
  khonggian: KG[r.space_type],
  phongcach: PC[r.design_style]
})

export const searchSpaces = (q, k = 12) => get('/search', { q, k })
export const getSpace = id => get('/spaces/' + id)
export const getSimilar = (id, k = 8) => get('/spaces/' + id + '/similar', { k })
