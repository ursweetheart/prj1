<template>
  <main class="wrap est">
    <header class="projects-head">
      <div>
        <h1 class="projects-title">Ước tính chi phí</h1>
        <p class="projects-intro">
          Nhập loại nhà, diện tích và gói vật liệu để xem khoảng chi phí thiết kế và thi công nội thất, chia theo hạng mục.
        </p>
      </div>
    </header>

    <form class="form-grid est-form" novalidate @submit.prevent="run">
      <div class="form-grid est-grid">
        <div class="field">
          <label for="est-type">Loại nhà</label>
          <select id="est-type" v-model="input.loai_nha">
            <option v-for="o in HOUSES" :key="o.v" :value="o.v">{{ o.t }}</option>
          </select>
        </div>
        <div class="field" :class="{ bad: inputErr.dien_tich_m2 }">
          <label for="est-area">Diện tích (m²)</label>
          <input id="est-area" v-model="input.dien_tich_m2" type="number" inputmode="decimal" min="10" max="5000" step="any"
                 required :aria-invalid="!!inputErr.dien_tich_m2"
                 :aria-describedby="inputErr.dien_tich_m2 ? 'est-area-e' : null">
          <span v-if="inputErr.dien_tich_m2" id="est-area-e" class="field-err" role="alert">{{ inputErr.dien_tich_m2 }}</span>
        </div>
        <div class="field" :class="{ bad: inputErr.so_phong_ngu }">
          <label for="est-rooms">Số phòng ngủ</label>
          <input id="est-rooms" v-model="input.so_phong_ngu" type="number" inputmode="numeric" min="0" max="10" step="1"
                 :aria-invalid="!!inputErr.so_phong_ngu" :aria-describedby="inputErr.so_phong_ngu ? 'est-rooms-e' : null">
          <span v-if="inputErr.so_phong_ngu" id="est-rooms-e" class="field-err" role="alert">{{ inputErr.so_phong_ngu }}</span>
        </div>
        <div class="field">
          <label for="est-pack">Gói vật liệu</label>
          <select id="est-pack" v-model="input.goi">
            <option v-for="o in PACKAGES" :key="o.v" :value="o.v">{{ o.t }}</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary est-go" :disabled="busy">{{ busy ? 'Đang tính…' : 'Ước tính' }}</button>
      <p v-if="runErr" class="field-err" role="alert">{{ runErr }}</p>
    </form>

    <section v-if="result" class="est-result" aria-live="polite" aria-labelledby="est-total">
      <p class="est-label">{{ describe(asked) }}</p>
      <p id="est-total" class="est-total num">{{ formatRange(result.tong) }}</p>
      <ul class="est-lines">
        <li v-for="l in result.hang_muc" :key="l.ma">
          <span>{{ l.ten }}</span><span class="num">{{ formatRange(l) }}</span>
        </li>
      </ul>
      <p class="est-notice">Ước tính tham khảo, chưa phải báo giá. Chi phí thực tế phụ thuộc hiện trạng và lựa chọn vật liệu sau khảo sát.</p>
      <p v-if="result.mau" class="est-notice is-sample" role="note">Đơn giá mẫu, chưa phải báo giá của D3 Studio.</p>

      <!-- detailed estimate by email -> lead nguon='estimate' -->
      <div class="est-send">
        <button v-if="!showSend && !sent" class="btn btn-secondary" type="button" @click="showSend = true">
          Nhận bản chi tiết qua email
        </button>
        <div v-if="sent" class="form-ok" role="status"><span class="dot" aria-hidden="true"></span><p style="margin:0">{{ sent }}</p></div>
        <form v-else-if="showSend" class="form-grid" novalidate @submit.prevent="send">
          <div class="form-grid two">
            <div class="field" :class="{ bad: errors.ho_ten }">
              <label for="est-name">Họ tên</label>
              <input id="est-name" v-model="c.ho_ten" type="text" autocomplete="name" maxlength="100"
                     :aria-invalid="!!errors.ho_ten" :aria-describedby="errors.ho_ten ? 'est-name-e' : null">
              <span v-if="errors.ho_ten" id="est-name-e" class="field-err" role="alert">{{ errors.ho_ten }}</span>
            </div>
            <div class="field" :class="{ bad: errors.so_dien_thoai }">
              <label for="est-tel">Số điện thoại</label>
              <input id="est-tel" v-model="c.so_dien_thoai" type="tel" inputmode="tel" autocomplete="tel" maxlength="30"
                     :aria-invalid="!!errors.so_dien_thoai" :aria-describedby="errors.so_dien_thoai ? 'est-tel-e' : null">
              <span v-if="errors.so_dien_thoai" id="est-tel-e" class="field-err" role="alert">{{ errors.so_dien_thoai }}</span>
            </div>
          </div>
          <div class="field" :class="{ bad: errors.email }">
            <label for="est-mail">Email nhận bản chi tiết</label>
            <input id="est-mail" v-model="c.email" type="email" inputmode="email" autocomplete="email" maxlength="200"
                   :aria-invalid="!!errors.email" :aria-describedby="errors.email ? 'est-mail-e' : null">
            <span v-if="errors.email" id="est-mail-e" class="field-err" role="alert">{{ errors.email }}</span>
          </div>
          <label v-if="consented" class="est-check">
            <input v-model="c.gui_ho_so" type="checkbox">
            <span>Gửi kèm những không gian tôi đã xem, để tư vấn viên hiểu gu của tôi</span>
          </label>
          <div class="est-hp" aria-hidden="true">
            <label for="est-web">Website</label>
            <input id="est-web" v-model="c.website" type="text" tabindex="-1" autocomplete="off">
          </div>
          <p class="small" style="margin:0">
            Thông tin chỉ dùng để gửi bản ước tính và để tư vấn viên D3 Studio liên hệ lại, không chia sẻ cho bên thứ ba.
          </p>
          <p v-if="sendErr" class="field-err" role="alert">{{ sendErr }}</p>
          <button class="btn btn-primary est-go" :disabled="sending">{{ sending ? 'Đang gửi…' : 'Gửi bản chi tiết' }}</button>
        </form>
      </div>

      <section v-if="similar.length" class="est-projects" aria-labelledby="est-proj-h">
        <h2 id="est-proj-h" class="est-label">Dự án cùng loại của D3</h2>
        <div class="projects-grid">
          <router-link v-for="p in similar" :key="p.slug" class="project" :to="'/du-an/' + p.slug">
            <div class="project-img">
              <img :src="p.cover" :width="p.images[0].w" :height="p.images[0].h" alt="" loading="lazy" decoding="async">
            </div>
            <h3 class="project-name">{{ p.name }}</h3>
            <p class="project-meta">{{ LOAI_NAME[p.loai] }}</p>
          </router-link>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
/* Ước tính chi phí (UC10, seq-9, act-6): số học trên bảng đơn giá, không gọi AI, cùng đầu vào cho cùng kết quả. */
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { consent, estimate, sendEstimate } from '@/api'
import { LOAI_NAME, PROJECTS_LIST } from '@/data/projects'
import { formatRange } from '@/lib/money'

const HOUSES = [{ v: 'can_ho', t: 'Căn hộ / Chung cư' }, { v: 'nha_pho', t: 'Nhà phố' }, { v: 'biet_thu', t: 'Biệt thự' },
                { v: 'van_phong', t: 'Văn phòng' }, { v: 'thuong_mai', t: 'Thương mại / Showroom' }]
const PACKAGES = [{ v: 'co_ban', t: 'Cơ bản' }, { v: 'tieu_chuan', t: 'Tiêu chuẩn' }, { v: 'cao_cap', t: 'Cao cấp' }]
// building type -> project types on the site (projects carry no budget yet, so only the type is matched)
const PROJECT_TYPES = { can_ho: ['chung-cu'], nha_pho: ['nha-pho'], biet_thu: ['villa'], van_phong: ['van-phong'],
                        thuong_mai: ['showroom', 'lounge', 'fnb'] }

const route = useRoute()
const consented = consent.get() === 'yes'
const input = reactive({ loai_nha: 'can_ho', dien_tich_m2: '', so_phong_ngu: 2, goi: 'tieu_chuan' })
const inputErr = reactive({})
const asked = ref(null)
const result = ref(null)
const busy = ref(false)
const runErr = ref('')

const showSend = ref(false)
const shownAt = ref(0)
const c = reactive({ ho_ten: '', so_dien_thoai: '', email: '', gui_ho_so: false, website: '' })
const errors = reactive({})
const sending = ref(false)
const sendErr = ref('')
const sent = ref('')

const similar = computed(() => asked.value
  ? PROJECTS_LIST.filter(p => PROJECT_TYPES[asked.value.loai_nha].includes(p.loai)).slice(0, 3) : [])
const label = (list, v) => list.find(o => o.v === v)?.t || v
const describe = a => [label(HOUSES, a.loai_nha), a.dien_tich_m2 + ' m²', a.so_phong_ngu + ' phòng ngủ', label(PACKAGES, a.goi)].join(' · ')

function readInput() {
  for (const k of Object.keys(inputErr)) delete inputErr[k]
  const area = Number(input.dien_tich_m2)
  const rooms = input.so_phong_ngu === '' ? 2 : Number(input.so_phong_ngu)
  if (input.dien_tich_m2 === '' || !(area >= 10 && area <= 5000)) inputErr.dien_tich_m2 = 'Diện tích từ 10 đến 5000 m²'
  if (!Number.isInteger(rooms) || rooms < 0 || rooms > 10) inputErr.so_phong_ngu = 'Số phòng ngủ từ 0 đến 10'
  return Object.keys(inputErr).length ? null : { loai_nha: input.loai_nha, dien_tich_m2: area, so_phong_ngu: rooms, goi: input.goi }
}

async function run() {
  runErr.value = ''
  const body = readInput()
  if (!body) return
  busy.value = true
  try {
    result.value = await estimate(body)
    asked.value = body
    sent.value = ''; showSend.value = false; shownAt.value = Date.now()
  } catch (e) {
    runErr.value = e.status === 429 ? 'Bạn thao tác quá nhanh, vui lòng thử lại sau.' : 'Chưa tính được, vui lòng thử lại.'
  } finally { busy.value = false }
}

const phoneOf = v => { const p = v.replace(/[\s.\-()]/g, ''); return p.startsWith('+84') ? '0' + p.slice(3) : p }
const MESSAGES = { ho_ten: 'Vui lòng nhập họ tên', so_dien_thoai: 'Số điện thoại chưa đúng',
                   email: 'Vui lòng nhập email để nhận bản chi tiết', email_sai: 'Email chưa đúng' }

async function send() {
  sendErr.value = ''
  for (const k of Object.keys(errors)) delete errors[k]
  if (!c.ho_ten.trim()) errors.ho_ten = MESSAGES.ho_ten
  if (!/^0\d{9}$/.test(phoneOf(c.so_dien_thoai))) errors.so_dien_thoai = MESSAGES.so_dien_thoai
  if (!c.email.trim()) errors.email = MESSAGES.email
  else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(c.email.trim())) errors.email = MESSAGES.email_sai
  if (Object.keys(errors).length) return
  sending.value = true
  try {
    const r = await sendEstimate({ ...asked.value, ho_ten: c.ho_ten.trim(), so_dien_thoai: c.so_dien_thoai,
                                   email: c.email.trim(), trang: route.path, gui_ho_so: consented && c.gui_ho_so,
                                   website: c.website || null, t_ms: Date.now() - shownAt.value })
    sent.value = r.message
  } catch (e) {
    if (e.status === 422 && Array.isArray(e.detail)) {
      for (const d of e.detail) { const k = d.loc?.[d.loc.length - 1]; if (k in MESSAGES) errors[k] = k === 'email' && c.email ? MESSAGES.email_sai : MESSAGES[k] }
      if (!Object.keys(errors).length) sendErr.value = 'Thông tin chưa hợp lệ, vui lòng kiểm tra lại.'
    } else if (e.status === 429) sendErr.value = 'Bạn gửi quá nhanh, vui lòng thử lại sau ít phút.'
    else sendErr.value = 'Chưa gửi được, vui lòng kiểm tra kết nối và thử lại.'
  } finally { sending.value = false }
}
</script>

<style scoped>
.est { padding-bottom: clamp(48px, 7vw, 96px) }
.est-form { max-width: 880px }
@media (min-width: 760px) { .est-grid { grid-template-columns: 1.4fr 1fr 1fr 1fr } }
.field input, .field select { width: 100%; min-width: 0 }
.est-go { justify-self: start }
@media (max-width: 480px) { .est-go { justify-self: stretch } }
.est-result { margin-top: clamp(32px, 5vw, 56px); padding-top: clamp(24px, 4vw, 40px); border-top: 1px solid var(--line-soft);
              display: grid; gap: 14px; max-width: 880px }
.est-label { margin: 0; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--faint) }
.est-total { margin: 0; font-family: var(--font-display); font-size: clamp(28px, 4vw, 44px); line-height: 1.1; color: var(--ink) }
.est-lines { list-style: none; padding: 0; margin: 6px 0 0; display: grid; gap: 0 }
.est-lines li { display: flex; justify-content: space-between; gap: 16px; padding: 12px 0; border-bottom: 1px solid var(--line-soft);
                font-size: 15px; color: var(--ink-2); flex-wrap: wrap }
.est-notice { margin: 0; font-size: 13px; color: var(--dim) }
.est-notice.is-sample { color: var(--accent) }
.est-send { margin-top: 10px }
.est-send .form-grid { max-width: 640px }
.est-check { display: flex; gap: 10px; align-items: flex-start; font-size: var(--text-sm); color: var(--dim); cursor: pointer }
.est-check input { margin-top: 3px; width: 18px; height: 18px; flex: none; accent-color: var(--accent) }
.est-hp { position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden }
.est-projects { margin-top: clamp(24px, 4vw, 40px); display: grid; gap: 16px }
</style>
