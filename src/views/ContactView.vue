<template>
  <main class="wrap wrap-wide page-top ct-page">
    <p class="eyebrow">Liên hệ</p>
    <h1 class="h-2" style="margin-top:10px">Nói với chúng tôi về không gian của bạn</h1>
    <p class="lead" style="margin-top:10px">
      Để lại số điện thoại, kiến trúc sư của {{ STUDIO.ten }} sẽ gọi lại. Hoặc gọi, nhắn Zalo trực tiếp.
    </p>

    <div class="ct-grid">
      <!-- seq-5: no project here, so the lead records the page /lien-he -->
      <ContactForm title="Gửi yêu cầu tư vấn" />

      <aside class="ct-side" aria-label="Thông tin liên hệ">
        <section id="zalo" class="ct-card" aria-labelledby="ct-call">
          <h2 id="ct-call" class="ct-h">Gọi hoặc nhắn</h2>
          <dl class="ct-list">
            <div>
              <dt>Điện thoại</dt>
              <dd><a v-if="telHref(STUDIO.dien_thoai)" :href="telHref(STUDIO.dien_thoai)">{{ STUDIO.dien_thoai.gia_tri }}</a>
                <span v-else>{{ STUDIO.dien_thoai.gia_tri }}</span><SampleMark v-if="STUDIO.dien_thoai.mau" /></dd>
            </div>
            <div>
              <dt>Zalo</dt>
              <dd><a v-if="zaloHref(STUDIO.zalo)" :href="zaloHref(STUDIO.zalo)" target="_blank" rel="noopener">Nhắn Zalo {{ STUDIO.zalo.gia_tri }}</a>
                <span v-else>{{ STUDIO.zalo.gia_tri }}</span><SampleMark v-if="STUDIO.zalo.mau" /></dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd><a v-if="mailHref(STUDIO.email)" :href="mailHref(STUDIO.email)">{{ STUDIO.email.gia_tri }}</a>
                <span v-else>{{ STUDIO.email.gia_tri }}</span><SampleMark v-if="STUDIO.email.mau" /></dd>
            </div>
          </dl>
        </section>

        <section id="ban-do" class="ct-card" aria-labelledby="ct-office">
          <h2 id="ct-office" class="ct-h">Văn phòng</h2>
          <dl class="ct-list">
            <div>
              <dt>Địa chỉ</dt>
              <dd>{{ STUDIO.dia_chi.gia_tri }}<SampleMark v-if="STUDIO.dia_chi.mau" /></dd>
            </div>
            <div>
              <dt>Giờ làm việc</dt>
              <dd>{{ STUDIO.gio_lam.gia_tri }}<SampleMark v-if="STUDIO.gio_lam.mau" /></dd>
            </div>
          </dl>
          <a v-if="mapHref(STUDIO.dia_chi)" class="pv-nav-link glow-hover ct-map" :href="mapHref(STUDIO.dia_chi)"
             target="_blank" rel="noopener">Mở bản đồ <span aria-hidden="true">↗</span></a>
          <p v-else class="small ct-note">Bản đồ sẽ hiện khi có địa chỉ thật.</p>
        </section>

        <section class="ct-card" aria-labelledby="ct-later">
          <h2 id="ct-later" class="ct-h">Chưa sẵn sàng gọi?</h2>
          <router-link class="pv-nav-link glow-hover" to="/uoc-tinh">Ước tính chi phí sơ bộ <span aria-hidden="true">→</span></router-link>
          <router-link class="pv-nav-link glow-hover" to="/trac-nghiem">Tìm phong cách hợp với bạn <span aria-hidden="true">→</span></router-link>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup>
/* Trang Liên hệ (roadmap 0.3, 2.3; seq-5). Thông tin studio đọc từ src/data/studio.js; giá trị mẫu không thành link. */
import { h, nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import ContactForm from '@/components/ContactForm.vue'
import { STUDIO, mailHref, mapHref, telHref, zaloHref } from '@/data/studio'

const SampleMark = () => h('span', { class: 'mau', title: 'Thông tin mẫu, chưa phải thông tin thật',
  'aria-label': 'thông tin mẫu, chưa phải thông tin thật' }, 'Thông tin mẫu')

/* The router offsets a hash by 110px, which the stacked phone header covers: scroll again with scroll-margin-top */
const route = useRoute()
async function toHash() {
  if (!['#zalo', '#ban-do'].includes(route.hash)) return
  await nextTick()
  document.querySelector(route.hash)?.scrollIntoView({ block: 'start' })
}
onMounted(() => setTimeout(toHash, 0)) // after the router's own scroll
watch(() => route.hash, toHash)

const baseTitle = document.title
document.title = 'Liên hệ — ' + STUDIO.ten
onBeforeUnmount(() => { document.title = baseTitle })
</script>

<style scoped>
.ct-page { padding-bottom: clamp(40px, 6vw, 80px) }
.ct-grid { display: grid; gap: clamp(28px, 4vw, 56px); margin-top: clamp(28px, 4vw, 48px); align-items: start }
@media (min-width: 900px) { .ct-grid { grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) } }
.ct-side { display: grid; gap: 16px; min-width: 0 }
.ct-card { display: grid; gap: 10px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel);
           padding: 18px 20px; min-width: 0; scroll-margin-top: 232px }
@media (min-width: 1024px) { .ct-card { scroll-margin-top: 128px } }
.ct-h { margin: 0; font-size: 16px; font-weight: 500; color: var(--ink) }
.ct-list { margin: 0; display: grid; gap: 10px }
.ct-list dt { font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--faint) }
.ct-list dd { margin: 2px 0 0; color: var(--ink-2); overflow-wrap: anywhere }
.ct-list a { color: var(--ink) }
.ct-note { margin: 0; color: var(--faint) }
.mau { display: inline-block; margin-left: 8px; padding: 1px 7px; border: 1px dashed var(--line); border-radius: 999px;
       font-size: 11px; color: var(--faint); vertical-align: 1px; white-space: nowrap }
</style>
