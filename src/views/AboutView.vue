<template>
  <main class="wrap wrap-wide page-top ab-page">
    <p class="eyebrow">Về chúng tôi</p>
    <h1 class="h-2" style="margin-top:10px">Về {{ STUDIO.ten }}</h1>
    <p class="lead" style="margin-top:10px">{{ STUDIO.mo_ta.gia_tri }}<SampleMark v-if="STUDIO.mo_ta.mau" /></p>

    <ul class="ab-figures" aria-label="Con số">
      <li><span class="ab-v num">{{ projectCount }}</span><span class="ab-k">dự án trên website</span></li>
      <li><span class="ab-v num">{{ typeCount }}</span><span class="ab-k">loại công trình</span></li>
      <li><span class="ab-v">Hà Nội</span><span class="ab-k">nơi đặt văn phòng</span></li>
    </ul>

    <section class="ab-sec" aria-labelledby="ab-team">
      <h2 id="ab-team" class="h-4">Đội ngũ</h2>
      <ul class="ab-team">
        <li v-for="p in STUDIO.doi_ngu" :key="p.ten" class="ab-card">
          <span class="ab-initials" aria-hidden="true">{{ initials(p.ten) }}</span>
          <span class="ab-name">{{ p.ten }}</span>
          <span class="ab-role">{{ p.vai_tro.gia_tri }}<SampleMark v-if="p.vai_tro.mau" /></span>
        </li>
      </ul>
    </section>

    <section class="ab-sec" aria-labelledby="ab-steps">
      <h2 id="ab-steps" class="h-4">Cách chúng tôi làm việc<SampleMark v-if="STUDIO.quy_trinh.mau" /></h2>
      <ol class="ab-steps">
        <li v-for="s in STUDIO.quy_trinh.buoc" :key="s.ten">
          <span class="ab-step">{{ s.ten }}</span>
          <span class="ab-step-d">{{ s.mo_ta }}</span>
        </li>
      </ol>
    </section>

    <nav class="ab-next" aria-label="Tiếp theo">
      <router-link class="pv-nav-link glow-hover" to="/du-an">Xem dự án <span aria-hidden="true">→</span></router-link>
      <router-link class="pv-nav-link glow-hover" to="/lien-he">Liên hệ <span aria-hidden="true">→</span></router-link>
    </nav>
  </main>
</template>

<script setup>
/* Trang Về chúng tôi (roadmap 0.3). Thông tin đọc từ src/data/studio.js; số dự án đọc (không sửa) từ src/data/projects.js. */
import { h, onBeforeUnmount } from 'vue'
import { PROJECTS_LIST } from '@/data/projects'
import { STUDIO } from '@/data/studio'

const SampleMark = () => h('span', { class: 'mau', title: 'Thông tin mẫu, chưa phải thông tin thật',
  'aria-label': 'thông tin mẫu, chưa phải thông tin thật' }, 'Thông tin mẫu')

const projectCount = PROJECTS_LIST.length
const typeCount = new Set(PROJECTS_LIST.map(p => p.loai)).size
const initials = name => name.split(' ').filter(Boolean).slice(-2).map(w => w[0]).join('')

const baseTitle = document.title
document.title = 'Về chúng tôi — ' + STUDIO.ten
onBeforeUnmount(() => { document.title = baseTitle })
</script>

<style scoped>
.ab-page { padding-bottom: clamp(40px, 6vw, 80px) }
.ab-figures { list-style: none; padding: 0; margin: clamp(28px, 4vw, 48px) 0 0; display: grid; gap: 14px;
              grid-template-columns: repeat(auto-fit, minmax(min(100%, 180px), 1fr)) }
.ab-figures li { display: grid; gap: 4px; border-top: 1px solid var(--line); padding-top: 14px }
.ab-v { font-family: var(--font-display); font-size: clamp(28px, 3.4vw, 40px); color: var(--ink) }
.ab-k { font-size: 13px; color: var(--dim) }
.ab-sec { margin-top: clamp(36px, 5vw, 64px) }
.ab-team { list-style: none; padding: 0; margin: 18px 0 0; display: grid; gap: 14px;
           grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)) }
.ab-card { display: grid; gap: 6px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel);
           padding: 18px 20px; min-width: 0 }
.ab-initials { width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center; font-size: 15px;
               color: var(--ink); border: 1px solid var(--line); margin-bottom: 6px }
.ab-name { color: var(--ink); font-size: 16px }
.ab-role { color: var(--dim); font-size: 14px }
.ab-steps { margin: 18px 0 0; padding: 0; list-style: none; counter-reset: step; display: grid; gap: 14px;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)) }
.ab-steps li { counter-increment: step; display: grid; gap: 6px; border-top: 1px solid var(--line); padding-top: 14px; min-width: 0 }
.ab-steps li::before { content: counter(step, decimal-leading-zero); font-size: 12px; color: var(--faint); letter-spacing: .06em }
.ab-step { color: var(--ink); font-size: 15px }
.ab-step-d { color: var(--dim); font-size: 14px; line-height: 1.55 }
.ab-next { margin-top: clamp(36px, 5vw, 64px); display: flex; flex-wrap: wrap; gap: 14px 32px }
.mau { display: inline-block; margin-left: 8px; padding: 1px 7px; border: 1px dashed var(--line); border-radius: 999px;
       font-size: 11px; font-weight: 400; color: var(--faint); vertical-align: 2px; white-space: nowrap; letter-spacing: 0 }
</style>
