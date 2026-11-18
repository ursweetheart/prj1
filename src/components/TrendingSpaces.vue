<template>
  <section v-if="items.length" class="trend wrap" aria-labelledby="trend-title">
    <div class="trend-in">
      <h2 id="trend-title" class="trend-title">Đang được quan tâm</h2>
      <ul class="trend-grid">
        <li v-for="s in items" :key="s.id">
          <router-link class="trend-card" :to="'/khong-gian/' + s.id">
            <div class="trend-img"><img :src="imageUrl(s.relative_path)" :alt="s.alt_text || s.nhan" loading="lazy" decoding="async"></div>
            <span class="trend-why">{{ s.nhan }}</span>
          </router-link>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
/* Homepage "Đang được quan tâm" (tracking-pipeline; act-3 "Điều chỉnh gợi ý trên trang chủ"): spaces chosen from the
 * values the leadership prioritised, the visitor's own viewing (only with personalisation consent) and the trends.
 * Shown only when the backend answers and has something to show. */
import { onMounted, ref } from 'vue'
import { getHomeSuggestions, imageUrl } from '@/api'
import { aiAvailable } from '@/lib/projectSpaces'

const items = ref([])
onMounted(async () => {
  if (!(await aiAvailable())) return
  try { items.value = await getHomeSuggestions() } catch { items.value = [] } // never an error on the homepage
})
</script>

<style scoped>
.trend { max-width: 1120px; padding-bottom: clamp(32px, 5vw, 56px) }
.trend-in { border-top: 1px solid var(--line-soft); padding-top: clamp(36px, 5vw, 60px) }
.trend-title { margin: 0 0 clamp(18px, 2.5vw, 28px); font-family: var(--font-display); font-weight: 300; color: var(--ink);
               font-size: clamp(22px, 2vw, 28px); letter-spacing: -0.01em }
.trend-grid { list-style: none; margin: 0; padding: 0; display: grid; gap: 16px; grid-template-columns: repeat(2, minmax(0, 1fr)) }
@media (min-width: 900px) { .trend-grid { grid-template-columns: repeat(4, minmax(0, 1fr)) } }
.trend-card { display: flex; flex-direction: column; gap: 8px; color: var(--ink); text-decoration: none }
.trend-card:focus-visible { box-shadow: var(--focus-ring); outline: none; border-radius: var(--radius-sm) }
.trend-img { aspect-ratio: 4 / 3; overflow: hidden; border-radius: var(--radius-sm); background: var(--panel) }
.trend-img img { width: 100%; height: 100%; object-fit: cover; transition: transform .4s }
.trend-card:hover img { transform: scale(1.03) }
.trend-why { font-size: 13px; line-height: 1.4; color: var(--dim) }
</style>
