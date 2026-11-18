<template>
  <main class="wrap page-top" style="padding-bottom:clamp(40px,6vw,96px);max-width:460px">
    <p class="eyebrow">Tài khoản</p>
    <h1 class="h-2" style="margin-top:10px">{{ session.user ? 'Tài khoản của bạn' : isRegister ? 'Tạo tài khoản' : 'Đăng nhập' }}</h1>

    <!-- admin-tools: a signed-in account sets its own full name here (class-6 NguoiDung.ho_ten) -->
    <form v-if="session.user" class="form-grid" style="margin-top:24px" @submit.prevent="saveName">
      <p class="small" style="margin:0">Đang đăng nhập: {{ session.user.email }}</p>
      <div class="field">
        <label for="my-name">Họ tên</label>
        <input id="my-name" v-model="myName" type="text" maxlength="100" autocomplete="name">
      </div>
      <p v-if="nameMsg" class="small" role="status">{{ nameMsg }}</p>
      <button class="btn btn-primary" :disabled="busy">Lưu họ tên</button>
    </form>
    <template v-else>

    <div class="stack" style="margin-top:28px;gap:10px">
      <a class="btn btn-secondary" :href="BACKEND + '/auth/google/login'">Tiếp tục với Google</a>
      <a class="btn btn-secondary" :href="BACKEND + '/auth/facebook/login'">Tiếp tục với Facebook</a>
    </div>
    <p class="small" style="margin:20px 0;text-align:center">hoặc dùng email</p>

    <form class="form-grid" @submit.prevent="submit">
      <div v-if="isRegister" class="field">
        <label for="reg-name">Họ tên <span class="small">(không bắt buộc)</span></label>
        <input id="reg-name" v-model="fullName" type="text" maxlength="100" autocomplete="name">
      </div>
      <div class="field" :class="{ bad: error }">
        <label for="email">Email</label>
        <input id="email" v-model.trim="email" type="email" autocomplete="email" required>
      </div>
      <div class="field" :class="{ bad: error }">
        <label for="pw">Mật khẩu</label>
        <input id="pw" v-model="password" type="password" minlength="8" maxlength="128" required
               :autocomplete="isRegister ? 'new-password' : 'current-password'">
        <span v-if="isRegister" class="field-help">Tối thiểu 8 ký tự.</span>
        <router-link v-else to="/quen-mat-khau" class="field-help lg-forgot">Quên mật khẩu?</router-link>
      </div>
      <p v-if="error" class="field-err" role="alert">{{ error }}</p>
      <button class="btn btn-primary" :disabled="busy">{{ isRegister ? 'Đăng ký' : 'Đăng nhập' }}</button>
    </form>

    <button class="btn btn-ghost" style="margin-top:16px" type="button" @click="isRegister = !isRegister; error = ''">
      {{ isRegister ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký' }}
    </button>
    </template>
  </main>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BACKEND, login, register, session, setMyName } from '@/api'

const route = useRoute()
const router = useRouter()
const isRegister = ref(false)
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)
const fullName = ref('')
const myName = ref(session.user?.ho_ten || '')
watch(() => session.user?.ho_ten, v => { if (!myName.value) myName.value = v || '' }) // the account loads after the page
const nameMsg = ref('')
async function saveName() {
  busy.value = true; nameMsg.value = ''
  try { await setMyName(myName.value); nameMsg.value = 'Đã lưu họ tên.' } catch (e) { nameMsg.value = e.message }
  finally { busy.value = false }
}

// a locked account coming back from Google / Facebook (user-admin): the server sends #loi=tai_khoan_bi_khoa
onMounted(() => {
  if (location.hash === '#loi=tai_khoan_bi_khoa') {
    error.value = 'Tài khoản đã bị khoá. Liên hệ quản trị viên.'
    history.replaceState(null, '', location.pathname + location.search)
  }
})

async function submit() {
  error.value = ''; busy.value = true
  try {
    await (isRegister.value ? register(email.value, password.value, fullName.value) : login(email.value, password.value))
    router.push(typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<style scoped>
.lg-forgot { justify-self: start; color: var(--dim) }
.lg-forgot:hover, .lg-forgot:focus-visible { color: var(--ink) }
</style>
