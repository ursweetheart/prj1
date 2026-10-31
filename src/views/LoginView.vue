<template>
  <main class="wrap" style="padding-block:clamp(40px,6vw,96px);max-width:460px">
    <p class="eyebrow">Tài khoản</p>
    <h1 class="h-2" style="margin-top:10px">{{ isRegister ? 'Tạo tài khoản' : 'Đăng nhập' }}</h1>

    <div class="stack" style="margin-top:28px;gap:10px">
      <a class="btn btn-secondary" :href="BACKEND + '/auth/google/login'">Tiếp tục với Google</a>
      <a class="btn btn-secondary" :href="BACKEND + '/auth/facebook/login'">Tiếp tục với Facebook</a>
    </div>
    <p class="small" style="margin:20px 0;text-align:center">hoặc dùng email</p>

    <form class="form-grid" @submit.prevent="submit">
      <div class="field" :class="{ bad: error }">
        <label for="email">Email</label>
        <input id="email" v-model.trim="email" type="email" autocomplete="email" required>
      </div>
      <div class="field" :class="{ bad: error }">
        <label for="pw">Mật khẩu</label>
        <input id="pw" v-model="password" type="password" minlength="8" maxlength="128" required
               :autocomplete="isRegister ? 'new-password' : 'current-password'">
        <span v-if="isRegister" class="field-help">Tối thiểu 8 ký tự.</span>
      </div>
      <p v-if="error" class="field-err" role="alert">{{ error }}</p>
      <button class="btn btn-primary" :disabled="busy">{{ isRegister ? 'Đăng ký' : 'Đăng nhập' }}</button>
    </form>

    <button class="btn btn-ghost" style="margin-top:16px" type="button" @click="isRegister = !isRegister; error = ''">
      {{ isRegister ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký' }}
    </button>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BACKEND, login, register } from '@/api'

const route = useRoute()
const router = useRouter()
const isRegister = ref(false)
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''; busy.value = true
  try {
    await (isRegister.value ? register : login)(email.value, password.value)
    router.push(typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/')
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>
