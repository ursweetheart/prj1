<template>
  <section class="cf bf" :aria-labelledby="uid + '-t'">
    <h2 :id="uid + '-t'" class="cf-title">Gửi bộ sưu tập cho kiến trúc sư</h2>

    <div v-if="done" class="form-ok bf-done" role="status">
      <span class="dot" aria-hidden="true"></span>
      <div>
        <p style="margin:0">{{ done.message }}</p>
        <p v-if="done.link" class="small" style="margin:8px 0 0">
          <router-link :to="done.path">Xem bộ sưu tập đã gửi</router-link>
          <button class="bf-copy" type="button" @click="copy">{{ copied ? 'Đã sao chép' : 'Sao chép link' }}</button>
        </p>
      </div>
    </div>

    <form v-else class="form-grid" novalidate @submit.prevent="submit">
      <p class="small bf-count">{{ items.length }} ảnh trong bộ sưu tập sẽ được gửi kèm, cùng ghi chú của bạn.</p>
      <div class="form-grid two">
        <div class="field" :class="{ bad: errors.ho_ten }">
          <label :for="uid + '-name'">Họ tên</label>
          <input :id="uid + '-name'" v-model="f.ho_ten" type="text" autocomplete="name" maxlength="100" required
                 :aria-invalid="!!errors.ho_ten" :aria-describedby="errors.ho_ten ? uid + '-name-e' : null">
          <span v-if="errors.ho_ten" :id="uid + '-name-e'" class="field-err" role="alert">{{ errors.ho_ten }}</span>
        </div>
        <div class="field" :class="{ bad: errors.so_dien_thoai }">
          <label :for="uid + '-tel'">Số điện thoại</label>
          <input :id="uid + '-tel'" v-model="f.so_dien_thoai" type="tel" inputmode="tel" autocomplete="tel" maxlength="30"
                 required :aria-invalid="!!errors.so_dien_thoai"
                 :aria-describedby="errors.so_dien_thoai ? uid + '-tel-e' : null">
          <span v-if="errors.so_dien_thoai" :id="uid + '-tel-e'" class="field-err" role="alert">{{ errors.so_dien_thoai }}</span>
        </div>
      </div>
      <div class="field" :class="{ bad: errors.email }">
        <label :for="uid + '-mail'">Email <span class="cf-opt">(không bắt buộc, để nhận link bộ sưu tập)</span></label>
        <input :id="uid + '-mail'" v-model="f.email" type="email" inputmode="email" autocomplete="email" maxlength="200"
               :aria-invalid="!!errors.email" :aria-describedby="errors.email ? uid + '-mail-e' : null">
        <span v-if="errors.email" :id="uid + '-mail-e'" class="field-err" role="alert">{{ errors.email }}</span>
      </div>
      <div class="form-grid bf-three">
        <div class="field" :class="{ bad: errors.loai_nha }">
          <label :for="uid + '-house'">Loại nhà</label>
          <select :id="uid + '-house'" v-model="f.loai_nha" required :aria-invalid="!!errors.loai_nha"
                  :aria-describedby="errors.loai_nha ? uid + '-house-e' : null">
            <option value="" disabled>Chọn loại nhà</option>
            <option v-for="o in HOUSES" :key="o.v" :value="o.v">{{ o.t }}</option>
          </select>
          <span v-if="errors.loai_nha" :id="uid + '-house-e'" class="field-err" role="alert">{{ errors.loai_nha }}</span>
        </div>
        <div class="field" :class="{ bad: errors.dien_tich_m2 }">
          <label :for="uid + '-area'">Diện tích (m²) <span class="cf-opt">(không bắt buộc)</span></label>
          <input :id="uid + '-area'" v-model="f.dien_tich_m2" type="number" inputmode="decimal" min="10" max="5000" step="any"
                 :aria-invalid="!!errors.dien_tich_m2" :aria-describedby="errors.dien_tich_m2 ? uid + '-area-e' : null">
          <span v-if="errors.dien_tich_m2" :id="uid + '-area-e'" class="field-err" role="alert">{{ errors.dien_tich_m2 }}</span>
        </div>
        <div class="field">
          <label :for="uid + '-budget'">Ngân sách</label>
          <select :id="uid + '-budget'" v-model="f.ngan_sach">
            <option v-for="o in BUDGETS" :key="o.v" :value="o.v">{{ o.t }}</option>
          </select>
        </div>
      </div>
      <div class="field" :class="{ bad: errors.loi_nhan }">
        <label :for="uid + '-msg'">Ghi chú <span class="cf-opt">(không bắt buộc)</span></label>
        <textarea :id="uid + '-msg'" v-model="f.loi_nhan" maxlength="1000" rows="3"
                  placeholder="Số phòng, thời gian dự kiến, điều bạn muốn giữ hoặc thay đổi…"
                  :aria-invalid="!!errors.loi_nhan" :aria-describedby="errors.loi_nhan ? uid + '-msg-e' : null"></textarea>
        <span v-if="errors.loi_nhan" :id="uid + '-msg-e'" class="field-err" role="alert">{{ errors.loi_nhan }}</span>
      </div>

      <label v-if="consented" class="cf-check">
        <input v-model="f.gui_ho_so" type="checkbox">
        <span>Gửi kèm những không gian tôi đã xem, để tư vấn viên hiểu gu của tôi</span>
      </label>

      <div class="cf-hp" aria-hidden="true">
        <label :for="uid + '-web'">Website</label>
        <input :id="uid + '-web'" v-model="f.website" type="text" tabindex="-1" autocomplete="off">
      </div>

      <p class="small cf-note">
        Thông tin và bộ sưu tập chỉ dùng để tư vấn viên D3 Studio liên hệ lại với anh/chị; link bộ sưu tập được gửi cho
        tư vấn viên. Không chia sẻ cho bên thứ ba.
      </p>
      <p v-if="failure" class="field-err" role="alert">{{ failure }}</p>
      <button class="btn btn-primary cf-send" :disabled="busy || !items.length">{{ busy ? 'Đang gửi…' : 'Gửi cho kiến trúc sư' }}</button>
    </form>
  </section>
</template>

<script setup>
/* Phiếu yêu cầu thiết kế (UC08, seq-7): bộ sưu tập + thông tin công trình -> khách tiềm năng nguồn 'brief'.
 * Cùng cách kiểm tra, chống spam và báo lỗi như ContactForm. */
import { reactive, ref, useId } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { consent, sendBrief } from '@/api'

const props = defineProps({
  items: { type: Array, required: true } // [{ space_id, ghi_chu }] as shown on the collection page
})

const HOUSES = [{ v: 'can_ho', t: 'Căn hộ / Chung cư' }, { v: 'nha_pho', t: 'Nhà phố' }, { v: 'biet_thu', t: 'Biệt thự' },
                { v: 'van_phong', t: 'Văn phòng' }, { v: 'thuong_mai', t: 'Thương mại / Showroom' }, { v: 'khac', t: 'Khác' }]
const BUDGETS = [{ v: 'chua_ro', t: 'Chưa rõ' }, { v: 'duoi_300tr', t: 'Dưới 300 triệu' }, { v: '300tr_700tr', t: '300 – 700 triệu' },
                 { v: '700tr_1500tr', t: '700 triệu – 1,5 tỷ' }, { v: 'tren_1500tr', t: 'Trên 1,5 tỷ' }]

const uid = 'bf' + useId()
const route = useRoute()
const router = useRouter()
const consented = consent.get() === 'yes'
const shownAt = Date.now()
const f = reactive({ ho_ten: '', so_dien_thoai: '', email: '', loai_nha: '', dien_tich_m2: '', ngan_sach: 'chua_ro',
                     loi_nhan: '', gui_ho_so: false, website: '' })
const errors = reactive({})
const failure = ref('')
const done = ref(null)
const busy = ref(false)
const copied = ref(false)

const MESSAGES = {
  ho_ten: 'Vui lòng nhập họ tên', so_dien_thoai: 'Số điện thoại chưa đúng', email: 'Email chưa đúng',
  loai_nha: 'Vui lòng chọn loại nhà', dien_tich_m2: 'Diện tích từ 10 đến 5000 m²', loi_nhan: 'Ghi chú tối đa 1000 ký tự',
  items: 'Bộ sưu tập chưa có ảnh nào đang hiển thị'
}
const phoneOf = v => { const p = v.replace(/[\s.\-()]/g, ''); return p.startsWith('+84') ? '0' + p.slice(3) : p }
const area = () => (f.dien_tich_m2 === '' || f.dien_tich_m2 === null ? null : Number(f.dien_tich_m2))
const checks = {
  ho_ten: () => f.ho_ten.trim() !== '',
  so_dien_thoai: () => /^0\d{9}$/.test(phoneOf(f.so_dien_thoai)),
  email: () => !f.email.trim() || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.trim()),
  loai_nha: () => !!f.loai_nha,
  dien_tich_m2: () => area() === null || (area() >= 10 && area() <= 5000),
  loi_nhan: () => f.loi_nhan.length <= 1000
}

function validate() {
  for (const k of Object.keys(MESSAGES)) delete errors[k]
  for (const [k, ok] of Object.entries(checks)) if (!ok()) errors[k] = MESSAGES[k]
  return !Object.keys(errors).length
}

async function submit() {
  failure.value = ''
  if (!validate()) return
  busy.value = true
  try {
    const r = await sendBrief({
      ho_ten: f.ho_ten.trim(), so_dien_thoai: f.so_dien_thoai, email: f.email.trim() || null,
      loai_nha: f.loai_nha, dien_tich_m2: area(), ngan_sach: f.ngan_sach, loi_nhan: f.loi_nhan.trim() || null,
      items: props.items, trang: route.path, gui_ho_so: consented && f.gui_ho_so, website: f.website || null,
      t_ms: Date.now() - shownAt
    })
    const path = r.ma_chia_se ? '/bo-suu-tap/xem/' + r.ma_chia_se : null
    done.value = { message: r.message, path, link: path && location.origin + router.resolve(path).href }
  } catch (e) {
    if (e.status === 422 && Array.isArray(e.detail)) {
      for (const d of e.detail) {
        const k = d.loc?.[d.loc.length - 1]
        if (k === 'items') failure.value = MESSAGES.items
        else if (MESSAGES[k]) errors[k] = MESSAGES[k]
      }
      if (!failure.value && !Object.keys(errors).length) failure.value = 'Thông tin chưa hợp lệ, vui lòng kiểm tra lại.'
    } else if (e.status === 429) {
      failure.value = 'Bạn gửi quá nhanh, vui lòng thử lại sau ít phút.'
    } else {
      failure.value = 'Chưa gửi được, vui lòng kiểm tra kết nối và thử lại.'
    }
  } finally {
    busy.value = false
  }
}

async function copy() {
  try { await navigator.clipboard.writeText(done.value.link); copied.value = true } catch { copied.value = false }
}
</script>

<style scoped>
.bf { max-width: none }
.cf { display: grid; gap: 20px }
.cf-title { margin: 0; font-size: clamp(20px, 2.2vw, 26px); font-weight: 500; letter-spacing: -.01em }
.cf-opt { color: var(--faint) }
.field input, .field textarea, .field select { width: 100%; min-width: 0 }
.bf-count { margin: 0; color: var(--dim) }
@media (min-width: 760px) { .bf-three { grid-template-columns: 1.3fr 1fr 1.2fr } }
.cf-check { display: flex; gap: 10px; align-items: flex-start; font-size: var(--text-sm); color: var(--dim); cursor: pointer }
.cf-check input { margin-top: 3px; width: 18px; height: 18px; flex: none; accent-color: var(--accent) }
.cf-hp { position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden }
.cf-note { margin: 0 }
.cf-send { justify-self: start }
.bf-copy { margin-left: 12px; background: none; border: 0; padding: 0; color: var(--dim); font: inherit; cursor: pointer;
           text-decoration: underline; text-underline-offset: 3px }
.bf-copy:hover, .bf-copy:focus-visible { color: var(--ink) }
.bf-done a { color: var(--ink); text-decoration: underline; text-underline-offset: 3px }
@media (max-width: 480px) { .cf-send { justify-self: stretch } }
</style>
