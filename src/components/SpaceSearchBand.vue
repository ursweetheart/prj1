<template>
  <section v-if="ai.state === 'on'" class="band wrap" aria-labelledby="band-title">
    <div class="band-in">
      <div>
        <p class="band-eyebrow">Không gian</p>
        <h2 id="band-title" class="band-title">Có một không gian bạn thích?</h2>
        <p class="band-text">Tìm không gian tương tự trong các dự án của D3 Studio, bằng một bức ảnh hoặc vài lời mô tả, hoặc làm trắc nghiệm để tìm phong cách hợp với bạn.</p>
      </div>
      <nav class="link-list band-links" aria-label="Tìm không gian">
        <button class="ll-item" type="button" @click="photoInput.click()">
          <span class="ll-n" aria-hidden="true">01</span><span class="ll-label">Tìm bằng ảnh</span><span class="ll-arrow" aria-hidden="true">→</span>
        </button>
        <router-link class="ll-item" :to="{ path: '/khong-gian', query: { tim: 'mo-ta' } }">
          <span class="ll-n" aria-hidden="true">02</span><span class="ll-label">Mô tả bằng lời</span><span class="ll-arrow" aria-hidden="true">→</span>
        </router-link>
        <router-link class="ll-item" to="/trac-nghiem">
          <span class="ll-n" aria-hidden="true">03</span><span class="ll-label">Trắc nghiệm phong cách</span><span class="ll-arrow" aria-hidden="true">→</span>
        </router-link>
      </nav>
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
.band-eyebrow { margin: 0; font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--faint) }
.band-title { margin: 14px 0 0; font-family: var(--font-display); font-weight: 300; color: var(--ink);
              font-size: clamp(28px, 3.4vw, 46px); line-height: 1.15; letter-spacing: -0.015em; text-wrap: balance }
.band-text { margin: 12px 0 0; max-width: 52ch; font-size: 14px; line-height: 1.6; color: var(--faint) }
.band-text { font-size: 15px }
</style>
