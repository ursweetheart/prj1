<template>
  <section v-if="ai.state === 'on'" class="band wrap" aria-labelledby="band-title">
    <div class="band-in">
      <div>
        <h2 id="band-title" class="band-title">Có một không gian bạn thích?</h2>
        <p class="band-text">Tìm không gian tương tự trong các dự án của D3 Studio, bằng một bức ảnh hoặc vài lời mô tả.</p>
      </div>
      <div class="band-links">
        <button class="cta-link glow-hover" type="button" @click="photoInput.click()">
          Tìm bằng ảnh <span class="arrow" aria-hidden="true">→</span>
        </button>
        <router-link class="cta-link glow-hover" :to="{ path: '/khong-gian', query: { tim: 'mo-ta' } }">
          Mô tả bằng lời <span class="arrow" aria-hidden="true">→</span>
        </router-link>
      </div>
      <input ref="photoInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="pick">
    </div>
  </section>
</template>

<script setup>
/* Dải giới thiệu mục "Không gian" ở trang chủ; chỉ hiện khi máy chủ AI trả lời.
 * Ô chọn ảnh nằm ngay ở đây (trình duyệt không cho mở hộp chọn file sau khi chuyển trang),
 * ảnh được chuyển sang /khong-gian để tìm luôn. */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ai, aiAvailable, setPendingPhoto } from '@/lib/projectSpaces'

aiAvailable()
const router = useRouter()
const photoInput = ref(null)

function pick(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  setPendingPhoto(file)
  router.push('/khong-gian')
}
</script>

<style scoped>
.band { max-width: 1120px; padding-bottom: clamp(40px, 6vw, 72px) }
.band-in { border-top: 1px solid var(--line-soft); padding-top: clamp(36px, 5vw, 60px);
           display: flex; flex-direction: column; gap: 24px }
@media (min-width: 900px) { .band-in { flex-direction: row; justify-content: space-between; align-items: flex-end; gap: 40px } }
.band-title { margin: 0; font-family: var(--font-display); font-weight: 300; color: var(--ink);
              font-size: clamp(22px, 2vw, 28px); letter-spacing: -0.01em }
.band-text { margin: 12px 0 0; max-width: 52ch; font-size: 14px; line-height: 1.6; color: var(--faint) }
.band-links { display: flex; flex-direction: column; align-items: flex-start; gap: 12px }
.band-links button.cta-link { border: 0; background: none; cursor: pointer; font-family: inherit }
</style>
