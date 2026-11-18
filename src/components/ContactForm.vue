<template>
  <section class="cf" :class="{ 'is-split': split }" :aria-labelledby="uid + '-t'">
    <header class="cf-intro">
      <p class="cf-eyebrow">{{ eyebrow }}</p>
      <h2 :id="uid + '-t'" class="cf-title">{{ title }}</h2>
      <p v-if="lead" class="cf-lead">{{ lead }}</p>
    </header>

    <div v-if="done" class="form-ok" role="status">
      <span class="dot" aria-hidden="true"></span>
      <p style="margin:0">{{ done }}</p>
    </div>

    <form v-else class="form-grid" novalidate @submit.prevent="submit">
      <div class="form-grid two">
        <div class="field" :class="{ bad: errors.ho_ten }">
          <label :for="uid + '-name'"><span class="cf-n" aria-hidden="true">01</span>Họ tên</label>
          <input :id="uid + '-name'" v-model="f.ho_ten" type="text" autocomplete="name" maxlength="100" required
                 :aria-invalid="!!errors.ho_ten" :aria-describedby="errors.ho_ten ? uid + '-name-e' : null">
          <span v-if="errors.ho_ten" :id="uid + '-name-e'" class="field-err" role="alert">{{ errors.ho_ten }}</span>
        </div>
        <div class="field" :class="{ bad: errors.so_dien_thoai }">
          <label :for="uid + '-tel'"><span class="cf-n" aria-hidden="true">02</span>Số điện thoại</label>
          <input :id="uid + '-tel'" v-model="f.so_dien_thoai" type="tel" inputmode="tel" autocomplete="tel"
                 maxlength="30" required
                 :aria-invalid="!!errors.so_dien_thoai" :aria-describedby="errors.so_dien_thoai ? uid + '-tel-e' : null">
          <span v-if="errors.so_dien_thoai" :id="uid + '-tel-e'" class="field-err" role="alert">{{ errors.so_dien_thoai }}</span>
        </div>
      </div>
      <div class="field" :class="{ bad: errors.email }">
        <label :for="uid + '-mail'"><span class="cf-n" aria-hidden="true">03</span>Email <span class="cf-opt">(không bắt buộc)</span></label>
        <input :id="uid + '-mail'" v-model="f.email" type="email" inputmode="email" autocomplete="email" maxlength="200"
               :aria-invalid="!!errors.email" :aria-describedby="errors.email ? uid + '-mail-e' : null">
        <span v-if="errors.email" :id="uid + '-mail-e'" class="field-err" role="alert">{{ errors.email }}</span>
      </div>
      <div class="field" :class="{ bad: errors.loi_nhan }">
        <label :for="uid + '-msg'"><span class="cf-n" aria-hidden="true">04</span>Lời nhắn <span class="cf-opt">(không bắt buộc)</span></label>
        <textarea :id="uid + '-msg'" v-model="f.loi_nhan" maxlength="1000" rows="3"
                  placeholder="Loại nhà, diện tích, thời gian dự kiến…"
                  :aria-invalid="!!errors.loi_nhan" :aria-describedby="errors.loi_nhan ? uid + '-msg-e' : null"></textarea>
        <span v-if="errors.loi_nhan" :id="uid + '-msg-e'" class="field-err" role="alert">{{ errors.loi_nhan }}</span>
      </div>

      <!-- second opt-in, only after the visitor accepted the banner: their own views go to a consultant (NĐ13) -->
      <label v-if="consented" class="cf-check">
        <input v-model="f.gui_ho_so" type="checkbox">
        <span class="cf-box" aria-hidden="true"></span>
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
      <button class="btn-line cf-send" :disabled="busy">
        <span>{{ busy ? 'Đang gửi…' : 'Gửi yêu cầu' }}</span><span class="arrow" aria-hidden="true">→</span>
      </button>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref, useId } from 'vue'
import { useRoute } from 'vue-router'
import { consent, createLead, trackEvent } from '@/api'

const props = defineProps({
  project: { type: String, default: null },   // project slug, when embedded on /du-an/<slug>
  spaceId: { type: Number, default: null },
  title: { type: String, default: 'Để lại thông tin, kiến trúc sư sẽ gọi lại' },
  eyebrow: { type: String, default: 'Liên hệ' },
  lead: { type: String, default: '' },
  split: { type: Boolean, default: false }   // intro on the left, form on the right from 900px
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
    trackEvent('gui_form', { doi_tuong: 'lien_he' }) // behaviour-events: which form, never its fields
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
/* Editorial form: light display title, hairline fields that draw an accent line on focus,
 * numbered labels, outline pill that fills on hover. Overrides the boxed global .field here only. */
.cf { --ease: cubic-bezier(0.22, 1, 0.36, 1); display: grid; gap: clamp(28px, 4vw, 44px); max-width: 720px }
.cf.is-split { max-width: none }
@media (min-width: 900px) {
  .cf.is-split { grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); column-gap: clamp(48px, 7vw, 120px); align-items: start }
  .cf.is-split .cf-intro { position: sticky; top: 140px }
}
.cf-intro { display: grid; gap: 14px; align-content: start }
.cf-eyebrow { margin: 0; font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--faint) }
.cf-title { margin: 0; max-width: 18ch; text-wrap: balance; font-family: var(--font-display); font-weight: 300;
            font-size: clamp(28px, 3.2vw, 44px); line-height: 1.15; letter-spacing: -0.015em; color: var(--ink) }
.cf-lead { margin: 4px 0 0; max-width: 40ch; font-size: 15px; line-height: 1.65; color: var(--faint) }

.form-grid { gap: clamp(22px, 2.6vw, 30px) }
.form-grid.two { column-gap: clamp(24px, 3vw, 40px) }
.field { gap: 4px }
.field label { display: flex; align-items: baseline; gap: 10px; font-size: 11.5px; letter-spacing: 0.14em;
               text-transform: uppercase; color: var(--faint); transition: color .35s var(--ease) }
.field:focus-within label { color: var(--ink-2) }
.cf-n { font-variant-numeric: tabular-nums; color: var(--accent); letter-spacing: 0.04em }
.cf-opt { text-transform: none; letter-spacing: 0; font-size: 12.5px; color: var(--faint); opacity: .75 }
.field input, .field textarea {
  width: 100%; min-width: 0; min-height: 0; padding: 10px 0 12px;
  font-family: var(--font-display); font-size: 17px; font-weight: 300; color: var(--ink);
  background: linear-gradient(var(--accent), var(--accent)) no-repeat 0 100% / 0% 1px;
  border: 0; border-bottom: 1px solid var(--line); border-radius: 0;
  transition: background-size .6s var(--ease), border-color .35s var(--ease);
}
.field textarea { min-height: 88px; resize: vertical; line-height: 1.55 }
.field input::placeholder, .field textarea::placeholder { color: var(--faint); opacity: .6; font-weight: 300 }
.field input:hover, .field textarea:hover { border-bottom-color: var(--faint) }
.field input:focus, .field textarea:focus,
.field input:focus-visible, .field textarea:focus-visible { outline: none; box-shadow: none; background-size: 100% 1px }
.field.bad input, .field.bad textarea { border-bottom-color: var(--accent) }
.field-err { margin-top: 6px }

.cf-check { position: relative; display: flex; gap: 12px; align-items: flex-start; font-size: var(--text-sm);
            line-height: 1.5; color: var(--dim); cursor: pointer }
.cf-check input { position: absolute; opacity: 0; width: 18px; height: 18px; margin: 0 }
.cf-box { flex: none; width: 16px; height: 16px; margin-top: 3px; border: 1px solid var(--faint);
          display: grid; place-items: center; transition: border-color .3s var(--ease), background-color .3s var(--ease) }
.cf-box::after { content: ""; width: 8px; height: 4px; margin-top: -2px; border: solid var(--accent-on);
                 border-width: 0 0 1.5px 1.5px; transform: rotate(-45deg) scale(0); transition: transform .3s var(--ease) }
.cf-check:hover .cf-box { border-color: var(--ink-2) }
.cf-check input:checked + .cf-box { background: var(--accent); border-color: var(--accent) }
.cf-check input:checked + .cf-box::after { transform: rotate(-45deg) scale(1) }
.cf-check input:focus-visible + .cf-box { box-shadow: var(--focus-ring) }

.cf-hp { position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden }
.cf-note { margin: 0; max-width: 56ch; font-size: 12.5px; line-height: 1.6; color: var(--faint) }

.cf-send { justify-self: start }
@media (max-width: 480px) { .cf-send { justify-self: stretch; justify-content: center } }
@media (prefers-reduced-motion: reduce) {
  .cf * { transition: none !important }
}
</style>
