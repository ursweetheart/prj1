<template>
  <main class="wrap page-top" style="padding-bottom:clamp(40px,6vw,96px);max-width:460px">
    <p class="eyebrow">Tài khoản</p>
    <h1 class="h-2" style="margin-top:10px">{{ info?.loai === 'moi' ? 'Kích hoạt tài khoản' : 'Đặt lại mật khẩu' }}</h1>

    <p v-if="state === 'loading'" class="small" style="margin-top:20px">Đang kiểm tra liên kết…</p>

    <div v-else-if="state === 'gone'" class="stack" style="margin-top:20px;gap:12px" role="alert">
      <p style="margin:0">{{ goneMsg }}</p>
      <router-link to="/quen-mat-khau" class="btn btn-secondary">Gửi liên kết mới</router-link>
    </div>

    <form v-else class="form-grid" style="margin-top:24px" novalidate @submit.prevent="submit">
      <p class="small" style="margin:0">
        {{ info.loai === 'moi' ? 'Đặt mật khẩu cho tài khoản' : 'Mật khẩu mới cho tài khoản' }} <strong>{{ info.email_an }}</strong>.
        {{ info.loai === 'dat_lai' ? 'Các phiên đăng nhập khác sẽ bị đăng xuất.' : '' }}
      </p>
      <div class="field" :class="{ bad: errors.pw }">
        <label for="sp-pw">Mật khẩu mới</label>
        <input id="sp-pw" v-model="pw" type="password" autocomplete="new-password" minlength="8" maxlength="128" required
               :aria-invalid="!!errors.pw" aria-describedby="sp-help">
        <span id="sp-help" class="field-help">Tối thiểu 8 ký tự.</span>
        <span v-if="errors.pw" class="field-err" role="alert">{{ errors.pw }}</span>
      </div>
      <div class="field" :class="{ bad: errors.again }">
        <label for="sp-again">Nhập lại mật khẩu</label>
        <input id="sp-again" v-model="again" type="password" autocomplete="new-password" maxlength="128" required
               :aria-invalid="!!errors.again" :aria-describedby="errors.again ? 'sp-again-e' : null">
        <span v-if="errors.again" id="sp-again-e" class="field-err" role="alert">{{ errors.again }}</span>
      </div>
      <p v-if="error" class="field-err" role="alert">{{ error }}</p>
      <button class="btn btn-primary" :disabled="busy">{{ busy ? 'Đang lưu…' : 'Lưu mật khẩu' }}</button>
    </form>
  </main>
</template>

<script setup>
/* Đặt mật khẩu từ liên kết mời hoặc đặt lại (account-invites-reset). The code is read from #ma= and removed from the
   address bar at once, so it stays out of history; it is sent in the request body only. */
import { onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { EDITORS, linkInfo, setPasswordFromLink } from '@/api'

const router = useRouter()
const code = new URLSearchParams(location.hash.replace(/^#/, '')).get('ma') || ''
history.replaceState(history.state, '', location.pathname + location.search)

const state = ref('loading') // loading | ok | gone
const info = ref(null)
const goneMsg = ref('')
const pw = ref('')
const again = ref('')
const errors = reactive({ pw: '', again: '' })
const error = ref('')
const busy = ref(false)

const gone = e => { state.value = 'gone'; goneMsg.value = e.detail?.msg || 'Liên kết không hợp lệ.' }
if (!code) gone({})
else linkInfo(code).then(r => { info.value = r; state.value = 'ok' }, e => (e.status === 410 ? gone(e) : gone({ detail: { msg: e.message } })))

async function submit() {
  errors.pw = pw.value.length < 8 ? 'Mật khẩu cần ít nhất 8 ký tự.' : ''
  errors.again = !errors.pw && again.value !== pw.value ? 'Hai mật khẩu chưa khớp.' : ''
  if (errors.pw || errors.again) return document.getElementById(errors.pw ? 'sp-pw' : 'sp-again')?.focus()
  busy.value = true; error.value = ''
  try {
    const user = await setPasswordFromLink(code, pw.value)
    const role = user?.role
    router.replace(EDITORS.includes(role) ? '/quan-tri' : role === 'sales' ? '/quan-tri/xu-huong' : '/')
  } catch (e) {
    if (e.status === 410) gone(e)
    else error.value = e.message
  } finally { busy.value = false }
}

const baseTitle = document.title
document.title = 'Đặt mật khẩu — D3 Studio'
onBeforeUnmount(() => { document.title = baseTitle })
</script>
