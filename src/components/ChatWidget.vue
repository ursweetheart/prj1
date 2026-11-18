<template>
  <div class="chat">
    <section v-if="open" class="chat-panel" aria-label="Trợ lý D3 Studio">
      <header class="row" style="justify-content:space-between;padding:12px 16px">
        <strong>Trợ lý D3 Studio</strong>
        <button class="btn btn-ghost" type="button" aria-label="Đóng" @click="open = false">✕</button>
      </header>

      <div ref="log" class="chat-log" aria-live="polite">
        <p v-if="!turns.length" class="small">Hỏi về giá, quy trình, thời gian thi công hoặc đặt lịch tư vấn.</p>
        <div v-for="(t, i) in turns" :key="i" class="chat-turn" :class="t.role">
          <p>{{ t.content }}</p>
          <!-- assistant-project-results: example projects, best match first -->
          <ul v-if="t.projects?.length" class="chat-projects">
            <li v-for="pr in t.projects" :key="pr.folder">
              <router-link :to="projectLink(pr)" class="chat-project" @click="open = false"
                           :aria-label="'Dự án ' + projectName(pr) + (pr.khop.length ? ', khớp ' + pr.khop.map(k => k.ten).join(', ') : '')">
                <span class="chat-project-imgs">
                  <img v-for="a in pr.anh" :key="a.id" :src="imageUrl(a.relative_path)" alt="" loading="lazy">
                </span>
                <span class="chat-project-text">
                  <strong>{{ projectName(pr) }}</strong>
                  <span v-if="pr.khop.length" class="small">{{ pr.khop.map(k => k.ten).join(' · ') }}</span>
                </span>
              </router-link>
            </li>
          </ul>
          <div v-else-if="t.images?.length" class="row g6" style="margin-top:8px;flex-wrap:wrap">
            <router-link v-for="im in t.images" :key="im.id" :to="'/khong-gian/' + im.id" @click="open = false">
              <img :src="imageUrl(im.relative_path)" alt="Dự án gợi ý" loading="lazy"
                   style="width:84px;height:64px;object-fit:cover;border-radius:var(--radius-sm)">
            </router-link>
          </div>
          <p v-if="t.sources?.length" class="small" style="margin-top:6px">Nguồn: {{ t.sources.map(s => s.title).join(', ') }}</p>
        </div>
        <p v-if="busy" class="small">Đang trả lời…</p>
        <p v-if="error" class="small" style="color:var(--danger)" role="alert">{{ error }}</p>
      </div>

      <form class="chat-form" @submit.prevent="send">
        <input v-model.trim="contact" type="text" maxlength="200" placeholder="Số điện thoại hoặc email (không bắt buộc)"
               aria-label="Liên hệ">
        <!-- lead-intake: second opt-in, shown only after the visitor accepted the consent banner -->
        <label v-if="consented" class="chat-check small">
          <input v-model="sendViews" type="checkbox">
          <span>Gửi kèm những không gian tôi đã xem cho kiến trúc sư</span>
        </label>
        <button v-if="turns.length" class="chat-new small" type="button" :disabled="busy" @click="startOver">
          Bắt đầu cuộc mới</button>
        <div class="row g6">
          <input ref="input" v-model="message" type="text" maxlength="1000" placeholder="Nhập câu hỏi…" aria-label="Câu hỏi" required style="flex:1">
          <button class="btn btn-primary" :disabled="busy">Gửi</button>
        </div>
        <p class="chat-note">Hội thoại được lưu ẩn danh 90 ngày để cải thiện trợ lý. Đừng gửi thông tin nhạy cảm.</p>
      </form>
    </section>

    <button class="chat-fab glow-hover" type="button" :aria-expanded="String(open)" @click="open = !open">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 18.5V6.8A1.8 1.8 0 0 1 6.8 5h10.4A1.8 1.8 0 0 1 19 6.8v7.4a1.8 1.8 0 0 1-1.8 1.8H8.6L5 18.5z"/>
      </svg>
      <span>{{ open ? 'Thu gọn' : 'Hỏi trợ lý' }}</span>
    </button>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { consent, deleteChat, getChat, imageUrl, sendChat, trackEvent } from '@/api'
import { projectBySlug } from '@/data/projects'
import { projectPhotoHref, slugOf } from '@/lib/projectSpaces'

/* a card opens the project page on its best photo when the folder has one, else that photo's space page */
const projectName = pr => projectBySlug(slugOf(pr.folder))?.name || pr.folder.replaceAll('_', ' ')
const projectLink = pr => (projectBySlug(slugOf(pr.folder)) ? projectPhotoHref(pr.anh[0].relative_path) : '/khong-gian/' + pr.anh[0].id)

const open = ref(false)
const turns = ref([])
const message = ref('')
const contact = ref('')
const busy = ref(false)
const error = ref('')
const log = ref(null)
const sendViews = ref(false)
const consented = ref(false)
const input = ref(null)
watch(open, o => {
  if (!o) return
  consented.value = consent.get() === 'yes' // the banner may be answered meanwhile
  restore()
})

/* chat-history: the conversation id lives in localStorage with consent (restored on a later visit), otherwise in
   sessionStorage (this tab only, survives a reload). Holding the id is what opens the conversation. */
const KEY = 'd3_hoi_thoai'
const store = () => (consent.get() === 'yes' ? localStorage : sessionStorage)
const getId = () => { try { return store().getItem(KEY) || sessionStorage.getItem(KEY) } catch { return null } }
function setId(id) {
  try {
    for (const s of [localStorage, sessionStorage]) s.removeItem(KEY)
    if (id) store().setItem(KEY, id)
  } catch { /* private mode: the conversation just isn't remembered */ }
}
let restored = false
async function restore() {
  if (restored || turns.value.length) return
  restored = true
  const id = getId()
  if (!id) return
  try {
    const r = await getChat(id)
    turns.value = r.tin_nhan.map(m => ({ role: m.vai_tro === 'khach' ? 'user' : 'assistant', content: m.noi_dung, sources: m.nguon }))
    setId(id) // move it to localStorage if the visitor accepted the banner since
    await nextTick(); log.value?.scrollTo(0, log.value.scrollHeight)
  } catch (e) { if (e.status === 404) setId(null) }
}
async function startOver() {
  const id = getId()
  turns.value = []; error.value = ''; setId(null)
  if (id) deleteChat(id).catch(() => {}) // gone from the server; a failure leaves it to the 90-day purge
  await nextTick(); input.value?.focus()
}

async function send() {
  const text = message.value
  if (!text || busy.value) return
  error.value = ''; busy.value = true; message.value = ''
  const history = turns.value.map(({ role, content }) => ({ role, content }))
  turns.value.push({ role: 'user', content: text })
  try {
    const r = await sendChat(text, history, contact.value, consented.value && sendViews.value, getId())
    if (r.hoi_thoai_id) setId(r.hoi_thoai_id)
    turns.value.push({ role: 'assistant', content: r.answer, images: r.images, projects: r.projects, sources: r.sources })
    trackEvent('nhan_chatbot') // behaviour-events: a count only, never the text
  } catch (e) { error.value = e.message } finally {
    busy.value = false
    await nextTick(); log.value?.scrollTo(0, log.value.scrollHeight)
  }
}
</script>

<style scoped>
.chat-check { display: flex; gap: 8px; align-items: flex-start; cursor: pointer }
.chat-check input { margin-top: 2px; flex: none; accent-color: var(--accent) }
.chat { position: fixed; right: 16px; bottom: 16px; z-index: 40; display: flex; flex-direction: column; align-items: flex-end; gap: 10px; color: var(--ink) }
.chat-panel { width: min(380px, calc(100vw - 32px)); max-height: min(560px, 80vh); display: flex; flex-direction: column;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--elev-raised) }
.chat-panel header { border-bottom: 1px solid var(--line) }
.chat-log { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 10px }
.chat-turn { max-width: 88%; padding: 10px 12px; border-radius: var(--radius-md); background: var(--line); white-space: pre-line }
.chat-turn.user { align-self: flex-end; background: var(--accent); color: var(--accent-on) }
.chat-projects { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 6px; white-space: normal }
.chat-project { display: flex; gap: 10px; align-items: center; padding: 6px; border-radius: var(--radius-sm);
  background: var(--page); color: var(--ink); text-decoration: none }
.chat-project:hover, .chat-project:focus-visible { outline: 2px solid var(--accent); outline-offset: 0 }
.chat-project-imgs { display: flex; gap: 4px; flex: none }
.chat-project-imgs img { width: 56px; height: 44px; object-fit: cover; border-radius: var(--radius-sm); display: block }
.chat-project-text { display: grid; gap: 2px; min-width: 0 }
.chat-project-text strong { overflow-wrap: anywhere }
.chat-form { display: grid; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--line) }
.chat-form input { background: transparent; color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md); padding: 10px 12px; min-height: 42px; min-width: 0 }
.chat-form input::placeholder { color: var(--faint) }
.chat-form input:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring) }
.chat-new { justify-self: start; background: none; border: 0; padding: 2px 0; color: var(--dim); cursor: pointer;
  text-decoration: underline; text-underline-offset: 3px; font: inherit; font-size: 13px }
.chat-new:hover, .chat-new:focus-visible { color: var(--ink) }
.chat-note { margin: 0; font-size: 11px; line-height: 1.45; color: var(--faint) }
/* Nút mở trợ lý: viên tối trong mờ, viền mảnh; hover giống topbar (.glow-hover) */
.chat-fab { display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer;
  font: inherit; font-size: 14px; letter-spacing: 0.02em; color: rgba(255, 255, 255, 0.88);
  background: rgba(20, 20, 19, 0.45); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.28); border-radius: var(--radius-pill);
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.45) }
.chat-fab svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.5;
  stroke-linejoin: round; filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.4)) }
.chat-fab:hover, .chat-fab:focus-visible { border-color: rgba(255, 255, 255, 0.6); color: #fff;
  text-shadow: 0 0 14px rgba(255, 255, 255, 0.55), 0 1px 10px rgba(0, 0, 0, 0.45);
  box-shadow: 0 0 18px rgba(255, 255, 255, 0.18); outline: none }
</style>
