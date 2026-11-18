<template>
  <main class="wrap wrap-wide page-top dv-page">
    <p class="eyebrow">Dịch vụ</p>
    <h1 class="h-2" style="margin-top:10px">Dịch vụ và quy trình</h1>
    <p class="lead" style="margin-top:10px">Những gói thiết kế {{ STUDIO.ten }} đang nhận, và các bước từ buổi gặp đầu tiên tới khi bàn giao.</p>

    <section class="dv-sec" aria-labelledby="dv-goi">
      <h2 id="dv-goi" class="h-4">Gói thiết kế</h2>
      <p v-if="services === null" class="small" style="margin-top:14px">Đang tải…</p>
      <p v-else-if="!services.length" class="small" style="margin-top:14px">Danh sách dịch vụ đang được cập nhật.</p>
      <ul v-else class="dv-list">
        <li v-for="s in services" :id="anchor(s.title)" :key="s.title" class="dv-card"
            :class="{ 'is-target': anchor(s.title) === target }">
          <h3 class="dv-name">{{ s.title }}<SampleMark v-if="s.mau" /></h3>
          <p class="dv-text">{{ s.content }}</p>
        </li>
      </ul>
    </section>

    <section class="dv-sec" aria-labelledby="dv-steps">
      <h2 id="dv-steps" class="h-4">Quy trình làm việc<SampleMark v-if="STUDIO.quy_trinh.mau" /></h2>
      <ol class="dv-steps">
        <li v-for="s in STUDIO.quy_trinh.buoc" :key="s.ten">
          <span class="dv-step">{{ s.ten }}</span>
          <span class="dv-step-d">{{ s.mo_ta }}</span>
        </li>
      </ol>
    </section>

    <nav class="dv-next" aria-label="Bước tiếp theo">
      <router-link class="pv-nav-link glow-hover" to="/trac-nghiem">Tìm phong cách của bạn <span aria-hidden="true">→</span></router-link>
      <router-link class="pv-nav-link glow-hover" to="/lien-he">Đặt lịch tư vấn <span aria-hidden="true">→</span></router-link>
    </nav>
  </main>
</template>

<script setup>
/* Trang Dịch vụ và quy trình (change visitor-services-hotspots). Gói dịch vụ đọc từ GET /services (các mục "service"
 * đang dùng của kho tri thức); không có backend thì dùng bản mẫu trong src/data/studio.js. Thẻ điểm nóng link tới
 * /dich-vu#<slug(tên gói)>, nên trang tự cuộn tới gói đó khi danh sách đã vẽ xong. */
import { h, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getServices } from '@/api'
import { STUDIO } from '@/data/studio'
import { slug } from '@/lib/slug'

const SampleMark = () => h('span', { class: 'mau', title: 'Thông tin mẫu, chưa phải thông tin thật',
  'aria-label': 'thông tin mẫu, chưa phải thông tin thật' }, 'Thông tin mẫu')

const route = useRoute()
const services = ref(null)
const anchor = title => slug(title)
const target = ref(decodeURIComponent(route.hash.slice(1)))

onMounted(async () => {
  try {
    services.value = await getServices()
  } catch {
    services.value = STUDIO.dich_vu.goi.map(g => ({ ...g, mau: STUDIO.dich_vu.mau }))
  }
  if (!target.value) return
  await nextTick()
  const el = document.getElementById(target.value)
  if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 110, behavior: 'smooth' })
})

const baseTitle = document.title
document.title = 'Dịch vụ và quy trình — ' + STUDIO.ten
onBeforeUnmount(() => { document.title = baseTitle })
</script>

<style scoped>
.dv-page { padding-bottom: clamp(40px, 6vw, 80px) }
.dv-sec { margin-top: clamp(36px, 5vw, 64px) }
.dv-list { list-style: none; padding: 0; margin: 18px 0 0; display: grid; gap: 14px;
           grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)) }
.dv-card { display: grid; gap: 8px; align-content: start; border: 1px solid var(--line); border-radius: var(--radius-md);
           background: var(--panel); padding: 20px 22px; min-width: 0; scroll-margin-top: 110px;
           transition: border-color .4s ease }
.dv-card.is-target { border-color: var(--ink-2) }
.dv-name { margin: 0; font-size: 17px; font-weight: 400; color: var(--ink) }
.dv-text { margin: 0; color: var(--dim); font-size: 14px; line-height: 1.6 }
.dv-steps { margin: 18px 0 0; padding: 0; list-style: none; counter-reset: step; display: grid; gap: 14px;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)) }
.dv-steps li { counter-increment: step; display: grid; gap: 6px; border-top: 1px solid var(--line); padding-top: 14px; min-width: 0 }
.dv-steps li::before { content: counter(step, decimal-leading-zero); font-size: 12px; color: var(--faint); letter-spacing: .06em }
.dv-step { color: var(--ink); font-size: 15px }
.dv-step-d { color: var(--dim); font-size: 14px; line-height: 1.55 }
.dv-next { margin-top: clamp(36px, 5vw, 64px); display: flex; flex-wrap: wrap; gap: 14px 32px }
.mau { display: inline-block; margin-left: 8px; padding: 1px 7px; border: 1px dashed var(--line); border-radius: 999px;
       font-size: 11px; font-weight: 400; color: var(--faint); vertical-align: 2px; white-space: nowrap; letter-spacing: 0 }
</style>
