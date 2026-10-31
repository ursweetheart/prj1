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
          <div v-if="t.images?.length" class="row g6" style="margin-top:8px;flex-wrap:wrap">
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
        <div class="row g6">
          <input v-model="message" type="text" maxlength="1000" placeholder="Nhập câu hỏi…" aria-label="Câu hỏi" required style="flex:1">
          <button class="btn btn-primary" :disabled="busy">Gửi</button>
        </div>
      </form>
    </section>

    <button class="btn btn-primary chat-fab" type="button" :aria-expanded="String(open)" @click="open = !open">
      {{ open ? 'Thu gọn' : 'Hỏi trợ lý' }}
    </button>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { imageUrl, sendChat } from '@/api'

const open = ref(false)
const turns = ref([])
const message = ref('')
const contact = ref('')
const busy = ref(false)
const error = ref('')
const log = ref(null)

async function send() {
  const text = message.value
  if (!text || busy.value) return
  error.value = ''; busy.value = true; message.value = ''
  const history = turns.value.map(({ role, content }) => ({ role, content }))
  turns.value.push({ role: 'user', content: text })
  try {
    const r = await sendChat(text, history, contact.value)
    turns.value.push({ role: 'assistant', content: r.answer, images: r.images, sources: r.sources })
  } catch (e) { error.value = e.message } finally {
    busy.value = false
    await nextTick(); log.value?.scrollTo(0, log.value.scrollHeight)
  }
}
</script>

<style scoped>
.chat { position: fixed; right: 16px; bottom: 16px; z-index: 40; display: flex; flex-direction: column; align-items: flex-end; gap: 10px; color: var(--ink) }
.chat-panel { width: min(380px, calc(100vw - 32px)); max-height: min(560px, 80vh); display: flex; flex-direction: column;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--elev-raised) }
.chat-panel header { border-bottom: 1px solid var(--line) }
.chat-log { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 10px }
.chat-turn { max-width: 88%; padding: 10px 12px; border-radius: var(--radius-md); background: var(--line); white-space: pre-line }
.chat-turn.user { align-self: flex-end; background: var(--accent); color: var(--accent-on) }
.chat-form { display: grid; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--line) }
.chat-form input { background: transparent; color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md); padding: 10px 12px; min-height: 42px; min-width: 0 }
.chat-form input::placeholder { color: var(--faint) }
.chat-form input:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring) }
.chat-fab { box-shadow: var(--elev-raised) }
</style>
