<template>
  <section class="cf" :aria-labelledby="uid + '-t'">
    <h2 :id="uid + '-t'" class="cf-title">{{ title }}</h2>

    <div v-if="done" class="form-ok" role="status">
      <span class="dot" aria-hidden="true"></span>
      <p style="margin:0">{{ done }}</p>
    </div>

    <form v-else class="form-grid" novalidate @submit.prevent="submit">
      <div class="form-grid two">
        <div class="field" :class="{ bad: errors.ho_ten }">
          <label :for="uid + '-name'">Họ tên</label>
          <input :id="uid + '-name'" v-model="f.ho_ten" type="text" autocomplete="name" maxlength="100" required
                 :aria-invalid="!!errors.ho_ten" :aria-describedby="errors.ho_ten ? uid + '-name-e' : null">
          <span v-if="errors.ho_ten" :id="uid + '-name-e'" class="field-err" role="alert">{{ errors.ho_ten }}</span>
        </div>
        <div class="field" :class="{ bad: errors.so_dien_thoai }">
          <label :for="uid + '-tel'">Số điện thoại</label>
          <input :id="uid + '-tel'" v-model="f.so_dien_thoai" type="tel" inputmode="tel" autocomplete="tel"
                 maxlength="30" required
                 :aria-invalid="!!errors.so_dien_thoai" :aria-describedby="errors.so_dien_thoai ? uid + '-tel-e' : null">
          <span v-if="errors.so_dien_thoai" :id="uid + '-tel-e'" class="field-err" role="alert">{{ errors.so_dien_thoai }}</span>
        </div>
      </div>
      <div class="field" :class="{ bad: errors.email }">
        <label :for="uid + '-mail'">Email <span class="cf-opt">(không bắt buộc)</span></label>
        <input :id="uid + '-mail'" v-model="f.email" type="email" inputmode="email" autocomplete="email" maxlength="200"
               :aria-invalid="!!errors.email" :aria-describedby="errors.email ? uid + '-mail-e' : null">
        <span v-if="errors.email" :id="uid + '-mail-e'" class="field-err" role="alert">{{ errors.email }}</span>
      </div>
      <div class="field" :class="{ bad: errors.loi_nhan }">
        <label :for="uid + '-msg'">Lời nhắn <span class="cf-opt">(không bắt buộc)</span></label>
        <textarea :id="uid + '-msg'" v-model="f.loi_nhan" maxlength="1000" rows="3"
                  placeholder="Loại nhà, diện tích, thời gian dự kiến…"
                  :aria-invalid="!!errors.loi_nhan" :aria-describedby="errors.loi_nhan ? uid + '-msg-e' : null"></textarea>
        <span v-if="errors.loi_nhan" :id="uid + '-msg-e'" class="field-err" role="alert">{{ errors.loi_nhan }}</span>
      </div>

      <!-- second opt-in, only after the visitor accepted the banner: their own views go to a consultant (NĐ13) -->
      <label v-if="consented" class="cf-check">
        <input v-model="f.gui_ho_so" type="checkbox">
        <span>Gửi kèm những không gian tôi đã xem, để tư vấn viên hiểu gu của tôi</span>
      </label>

      <!-- honeypot: off-screen and skipped by keyboard and screen readers; people leave it empty -->
      <div class="cf-hp" aria-hidden="true">
        <label :for="uid + '-web'">Website</label>
        <input :id="uid + '-web'" v-model="f.website" type="text" tabindex="-1" autocomplete="off">
      </div>

      <p class="small cf-note">
        Thông tin chỉ dùng để tư vấn viên D3 Studio liên hệ lại với anh/chị về yêu cầu này,
        không chia sẻ cho bên thứ ba.
      </p>
      <p v-if="failure" class="field-err" role="alert">{{ failure }}</p>
      <button class="btn btn-primary cf-send" :disabled="busy">{{ busy ? 'Đang gửi…' : 'Gửi yêu cầu' }}</button>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref, useId } from 'vue'
import { useRoute } from 'vue-router'
import { consent, createLead } from '@/api'

const props = defineProps({
  project: { type: String, default: null },   // project slug, when embedded on /du-an/<slug>
  spaceId: { type: Number, default: null },
  title: { type: String, default: 'Để lại thông tin, kiến trúc sư sẽ gọi lại' }
})

const uid = 'cf' + useId()
const route = useRoute()
const consented = consent.get() === 'yes'
const shownAt = Date.now()
const f = reactive({ ho_ten: '', so_dien_thoai: '', email: '', loi_nhan: '', gui_ho_so: false, website: '' })
const errors = reactive({})
const failure = ref('')
const done = ref('')
const busy = ref(false)

const MESSAGES = {
  ho_ten: 'Vui lòng nhập họ tên',
  so_dien_thoai: 'Số điện thoại chưa đúng',
  email: 'Email chưa đúng',
  loi_nhan: 'Lời nhắn tối đa 1000 ký tự'
}
// same rules as the server (backend/api.py LeadIn)
const phoneOf = v => { const p = v.replace(/[\s.\-()]/g, ''); return p.startsWith('+84') ? '0' + p.slice(3) : p }
const checks = {
  ho_ten: () => f.ho_ten.trim() !== '',
  so_dien_thoai: () => /^0\d{9}$/.test(phoneOf(f.so_dien_thoai)),
  email: () => !f.email.trim() || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.trim()),
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
    const r = await createLead({
      ho_ten: f.ho_ten.trim(), so_dien_thoai: f.so_dien_thoai, email: f.email.trim() || null,
      loi_nhan: f.loi_nhan.trim() || null, trang: route.path, du_an: props.project, space_id: props.spaceId,
      gui_ho_so: consented && f.gui_ho_so, website: f.website || null, t_ms: Date.now() - shownAt
    })
    done.value = r.message
  } catch (e) {
    if (e.status === 422 && Array.isArray(e.detail)) {
      for (const d of e.detail) { const k = d.loc?.[d.loc.length - 1]; if (MESSAGES[k]) errors[k] = MESSAGES[k] }
      if (!Object.keys(errors).length) failure.value = 'Thông tin chưa hợp lệ, vui lòng kiểm tra lại.'
    } else if (e.status === 429) {
      failure.value = 'Bạn gửi quá nhanh, vui lòng thử lại sau ít phút.'
    } else {
      failure.value = 'Chưa gửi được, vui lòng kiểm tra kết nối và thử lại.'
    }
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.cf { display: grid; gap: 20px; max-width: 720px }
.cf-title { margin: 0; font-size: clamp(20px, 2.2vw, 26px); font-weight: 500; letter-spacing: -.01em }
.cf-opt { color: var(--faint) }
.field input, .field textarea { width: 100%; min-width: 0 }
.cf-check { display: flex; gap: 10px; align-items: flex-start; font-size: var(--text-sm); color: var(--dim); cursor: pointer }
.cf-check input { margin-top: 3px; width: 18px; height: 18px; flex: none; accent-color: var(--accent) }
.cf-hp { position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden }
.cf-note { margin: 0 }
.cf-send { justify-self: start }
@media (max-width: 480px) { .cf-send { justify-self: stretch } }
</style>
