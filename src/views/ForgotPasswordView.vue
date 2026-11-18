<template>
  <main class="wrap page-top" style="padding-bottom:clamp(40px,6vw,96px);max-width:460px">
    <p class="eyebrow">Tài khoản</p>
    <h1 class="h-2" style="margin-top:10px">Quên mật khẩu</h1>

    <div v-if="done" class="form-ok" role="status" style="margin-top:24px">
      <span class="dot" aria-hidden="true"></span>
      <p style="margin:0">{{ done }}</p>
    </div>
    <form v-else class="form-grid" style="margin-top:24px" novalidate @submit.prevent="submit">
      <p class="small" style="margin:0">Nhập email tài khoản, chúng tôi gửi liên kết đặt lại mật khẩu (dùng được trong 1 giờ).</p>
      <div class="field" :class="{ bad: error }">
        <label for="fp-email">Email</label>
        <input id="fp-email" v-model.trim="email" type="email" autocomplete="email" required
               :aria-invalid="!!error" :aria-describedby="error ? 'fp-err' : null">
        <span v-if="error" id="fp-err" class="field-err" role="alert">{{ error }}</span>
      </div>
      <button class="btn btn-primary" :disabled="busy">{{ busy ? 'Đang gửi…' : 'Gửi liên kết' }}</button>
    </form>
    <router-link to="/dang-nhap" class="btn btn-ghost" style="margin-top:16px">Quay lại đăng nhập</router-link>
  </main>
</template>

<script setup>
/* Quên mật khẩu (account-invites-reset): the answer is the same whether or not the email has an account */
import { onBeforeUnmount, ref } from 'vue'
import { forgotPassword } from '@/api'

const email = ref('')
const error = ref('')
const done = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value)) { error.value = 'Nhập một địa chỉ email hợp lệ.'; return }
  busy.value = true
  try { done.value = (await forgotPassword(email.value)).message }
  catch (e) { error.value = e.status === 429 ? 'Bạn đã yêu cầu nhiều lần, hãy thử lại sau ít phút.' : e.message }
  finally { busy.value = false }
}

const baseTitle = document.title
document.title = 'Quên mật khẩu — D3 Studio'
onBeforeUnmount(() => { document.title = baseTitle })
</script>
