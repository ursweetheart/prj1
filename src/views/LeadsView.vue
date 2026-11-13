<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Kinh doanh</p>
    <h1 class="h-2" style="margin-top:10px">Khách để lại thông tin</h1>
    <p class="lead" style="margin-top:10px">
      Từ form liên hệ trên trang dự án và từ trợ lý chat. Liên hệ và theo dõi khách do đội tư vấn làm ngoài hệ thống.
    </p>

    <div class="row g6 leads-filter" role="group" aria-label="Lọc theo nguồn">
      <button v-for="o in FILTERS" :key="o.value" type="button" class="chip" :aria-pressed="String(nguon === o.value)"
              @click="nguon = o.value">{{ o.label }}</button>
    </div>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!leads.length" class="small" style="margin-top:20px">{{ loading ? 'Đang tải…' : 'Chưa có khách nào.' }}</p>

    <ul class="stack" style="margin-top:20px;gap:14px;list-style:none;padding:0">
      <li v-for="l in leads" :key="l.id" class="form-ok lead">
        <div class="row g10" style="flex-wrap:wrap">
          <span class="chip chip-static">{{ SOURCE_VI[l.nguon] || l.nguon }}</span>
          <span v-if="l.intent" class="chip chip-static">{{ INTENT_VI[l.intent] || l.intent }}</span>
          <strong>{{ l.ho_ten || l.contact || 'Chưa có liên hệ' }}</strong>
          <span class="small">{{ new Date(l.created_at).toLocaleString('vi-VN') }}</span>
        </div>

        <p v-if="l.so_dien_thoai || l.email" class="small lead-contact">
          <a v-if="l.so_dien_thoai" :href="'tel:' + l.so_dien_thoai">{{ l.so_dien_thoai }}</a>
          <a v-if="l.email" :href="'mailto:' + l.email">{{ l.email }}</a>
        </p>
        <p v-if="l.ho_ten && l.contact" class="small">Liên hệ để lại trong chat: {{ l.contact }}</p>
        <p v-if="l.loi_nhan" class="lead-msg">{{ l.loi_nhan }}</p>
        <p v-if="contextLink(l)" class="small">
          Từ: <router-link :to="contextLink(l).to">{{ contextLink(l).label }}</router-link>
        </p>
        <p v-else-if="l.ngu_canh?.trang && !['brief', 'estimate'].includes(l.nguon)" class="small">Từ trang {{ l.ngu_canh.trang }}</p>
        <p v-if="l.nguon === 'chat' && l.request" class="small">{{ summary(l.request) }}</p>

        <!-- estimate: what the visitor entered and the range the server computed -->
        <template v-if="l.nguon === 'estimate' && l.request?.ket_qua">
          <p class="small">{{ estimateFacts(l.request.dau_vao) }}</p>
          <p class="lead-brief-line num">{{ formatRange(l.request.ket_qua.tong) }}
            <span v-if="l.request.ket_qua.mau" class="small lead-sample">· đơn giá mẫu</span></p>
        </template>

        <!-- brief: the project facts, what the chosen photos share, the photos with the visitor's notes -->
        <template v-if="l.nguon === 'brief'">
          <p class="small">{{ briefFacts(l.request) }}</p>
          <p v-if="l.request?.tom_tat?.line" class="lead-brief-line">{{ l.request.tom_tat.line }}</p>
          <ul v-if="l.bo_suu_tap?.length" class="lead-brief-photos">
            <li v-for="s in l.bo_suu_tap" :key="s.id">
              <router-link :to="'/khong-gian/' + s.id" :aria-label="'Không gian ' + s.id + ' — ' + spaceLabel(s.space_type)">
                <img :src="imageUrl(s.relative_path)" alt="" loading="lazy" class="lead-thumb">
              </router-link>
              <span v-if="s.ghi_chu" class="small">“{{ s.ghi_chu }}”</span>
            </li>
          </ul>
          <p v-if="l.ma_chia_se" class="small">
            <router-link :to="'/bo-suu-tap/xem/' + l.ma_chia_se">Xem bộ sưu tập đã gửi</router-link>
          </p>
        </template>

        <details v-if="l.ho_so_hanh_vi" class="lead-profile">
          <summary class="small">Sở thích (khách đồng ý gửi): {{ l.tom_tat }}</summary>
          <div class="row g6" style="flex-wrap:wrap;margin-top:8px">
            <router-link v-for="s in l.ho_so_hanh_vi.spaces" :key="s.id" :to="'/khong-gian/' + s.id"
                         :aria-label="'Không gian ' + s.id + ' — ' + spaceLabel(s.space_type)">
              <img :src="imageUrl(s.relative_path)" alt="" loading="lazy" class="lead-thumb">
            </router-link>
          </div>
        </details>

        <details v-if="l.conversation?.length" style="margin-top:10px">
          <summary class="small">Hội thoại ({{ l.conversation.length }})</summary>
          <p v-for="(m, i) in l.conversation" :key="i" class="small" style="margin-top:6px">
            <strong>{{ m.role === 'user' ? 'Khách' : 'Trợ lý' }}:</strong> {{ m.content }}
          </p>
        </details>
      </li>
    </ul>
  </main>
</template>

<script setup>
import { ref, watch } from 'vue'
import { imageUrl, listLeads, spaceLabel } from '@/api'
import { projectBySlug } from '@/data/projects'
import { formatRange } from '@/lib/money'

const SOURCE_VI = { form: 'Form liên hệ', chat: 'Trợ lý chat', brief: 'Bộ sưu tập', estimate: 'Ước tính chi phí' }
const INTENT_VI = { price: 'Hỏi giá', appointment: 'Xin hẹn', handoff: 'Chuyển kiến trúc sư' }
const PROJECT_VI = { can_ho: 'Căn hộ', biet_thu: 'Biệt thự', nha_pho: 'Nhà phố', van_phong: 'Văn phòng', thuong_mai: 'Thương mại' }
const FILTERS = [{ value: null, label: 'Tất cả' }, { value: 'form', label: 'Form liên hệ' }, { value: 'brief', label: 'Bộ sưu tập' },
                 { value: 'estimate', label: 'Ước tính' },
                 { value: 'chat', label: 'Trợ lý chat' }]
const leads = ref([])
const loading = ref(true)
const error = ref('')
const nguon = ref(null)

// what the assistant understood from the question: only show the fields it found
function summary(req = {}) {
  return [PROJECT_VI[req.project_type], req.space_type && spaceLabel(req.space_type), req.design_style,
          req.area_m2 && req.area_m2 + ' m²'].filter(Boolean).join(' · ') || 'Chưa nhận diện được yêu cầu cụ thể'
}

const HOUSE_VI = { can_ho: 'Căn hộ / Chung cư', nha_pho: 'Nhà phố', biet_thu: 'Biệt thự', van_phong: 'Văn phòng',
                   thuong_mai: 'Thương mại / Showroom', khac: 'Khác' }
const BUDGET_VI = { duoi_300tr: 'Dưới 300 triệu', '300tr_700tr': '300 – 700 triệu', '700tr_1500tr': '700 triệu – 1,5 tỷ',
                    tren_1500tr: 'Trên 1,5 tỷ', chua_ro: 'Ngân sách chưa rõ' }
function briefFacts(r = {}) {
  return [HOUSE_VI[r.loai_nha], r.dien_tich_m2 && r.dien_tich_m2 + ' m²', BUDGET_VI[r.ngan_sach],
          r.tom_tat?.n && r.tom_tat.n + ' ảnh'].filter(Boolean).join(' · ')
}

const PACKAGE_VI = { co_ban: 'Cơ bản', tieu_chuan: 'Tiêu chuẩn', cao_cap: 'Cao cấp' }
function estimateFacts(d = {}) {
  return [HOUSE_VI[d.loai_nha], d.dien_tich_m2 + ' m²', d.so_phong_ngu + ' phòng ngủ', PACKAGE_VI[d.goi]].filter(Boolean).join(' · ')
}

function contextLink(l) {
  const c = l.ngu_canh || {}
  if (c.du_an) return { to: '/du-an/' + c.du_an, label: 'dự án ' + (projectBySlug(c.du_an)?.name || c.du_an) }
  if (c.space_id) return { to: '/khong-gian/' + c.space_id, label: 'không gian #' + c.space_id }
  return null
}

async function load() {
  loading.value = true; error.value = ''
  try { leads.value = await listLeads(nguon.value ? { nguon: nguon.value } : {}) }
  catch (e) { error.value = e.message } finally { loading.value = false }
}
watch(nguon, load, { immediate: true })
</script>

<style scoped>
.leads-filter { margin-top: 20px; flex-wrap: wrap }
.lead { display: block; min-width: 0; overflow-wrap: anywhere }
.lead > * + * { margin-top: 8px }
.lead-contact { display: flex; gap: 16px; flex-wrap: wrap }
.lead-msg { margin: 8px 0 0; white-space: pre-line }
.lead-profile { margin-top: 10px }
.lead-brief-line { margin: 8px 0 0; color: var(--ink) }
.lead-sample { color: var(--accent) }
.lead-brief-photos { list-style: none; padding: 0; margin: 10px 0 0; display: flex; flex-wrap: wrap; gap: 12px }
.lead-brief-photos li { display: grid; gap: 4px; max-width: 140px }
.lead-thumb { width: 84px; height: 64px; object-fit: cover; border-radius: var(--radius-sm); display: block }
</style>
