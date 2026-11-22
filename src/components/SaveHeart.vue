<template>
  <span class="heart-wrap" :class="{ 'is-labelled': labelled, 'is-overlay': overlay }">
    <button class="heart" type="button" :aria-pressed="String(saved)"
            :aria-label="saved ? 'Bỏ khỏi bộ sưu tập' : 'Lưu vào bộ sưu tập'"
            :title="saved ? 'Bỏ khỏi bộ sưu tập' : 'Lưu vào bộ sưu tập'"
            @click.prevent.stop="onClick">
      <Icon name="heart" :filled="saved" />
      <span v-if="labelled">{{ saved ? 'Đã lưu' : 'Lưu' }}</span>
    </button>
    <span v-if="message" class="heart-msg" role="alert">{{ message }}</span>
    <!-- seq-13 b3 (visitor-touchpoints): signed out, after the first save of the session -->
    <span v-else-if="invite" class="heart-msg heart-invite" role="status">
      Đã lưu vào bộ sưu tập. <router-link :to="{ path: '/dang-nhap', query: { next: route.fullPath } }">Đăng ký</router-link>
      để không mất bộ sưu tập.
      <button class="heart-x" type="button" aria-label="Đóng" @click.prevent.stop="invite = false">✕</button>
    </span>
  </span>
</template>

<script setup>
import Icon from '@/components/Icon.vue'
/* Trái tim lưu một không gian vào "Bộ sưu tập" (UC07). Không cần tài khoản: lib/collection.js giữ trong trình duyệt
 * cho đến khi khách đăng nhập. overlay: đặt ở góc ảnh của thẻ; labelled: kèm chữ, dùng ở trang không gian. */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { session } from '@/api'
import { collection, has, toggle } from '@/lib/collection'

const route = useRoute()
const INVITED = 'd3_moi_dang_ky' // once per browser session
const invite = ref(false)
function maybeInvite() {
  if (session.token) return
  try {
    if (sessionStorage.getItem(INVITED)) return
    sessionStorage.setItem(INVITED, '1')
  } catch { return } // private mode: no note rather than one on every save
  invite.value = true
  setTimeout(() => { invite.value = false }, 8000)
}

const props = defineProps({
  spaceId: { type: Number, required: true },
  labelled: { type: Boolean, default: false },
  overlay: { type: Boolean, default: false }
})
const saved = computed(() => has(props.spaceId))
const message = ref('')

async function onClick() {
  message.value = ''
  if (!(await toggle(props.spaceId))) message.value = collection.error
  else if (saved.value) maybeInvite()
}
</script>

<style scoped>
.heart-wrap { display: inline-flex; flex-direction: column; align-items: flex-end; gap: 6px }
.heart-wrap.is-overlay { position: absolute; top: 10px; right: 10px; z-index: 2 }
.heart { display: inline-flex; align-items: center; gap: 8px; min-width: 40px; min-height: 40px; padding: 0 10px;
         justify-content: center; border: 1px solid var(--line); border-radius: var(--radius-pill);
         background: color-mix(in oklab, var(--fg, #111) 62%, transparent); color: var(--ink); cursor: pointer;
         font: 500 11.5px/1 var(--font-body); letter-spacing: 0.14em; text-transform: uppercase;
         backdrop-filter: blur(6px);
         transition: border-color .45s cubic-bezier(0.22, 1, 0.36, 1), color .4s cubic-bezier(0.22, 1, 0.36, 1),
                     transform .3s cubic-bezier(0.22, 1, 0.36, 1) }
.is-labelled .heart { padding: 0 16px }
.heart:hover { border-color: color-mix(in oklab, var(--accent) 80%, white) }
.heart:focus-visible { outline: none; box-shadow: var(--focus-ring) }
.heart:active { transform: scale(.94) }
.heart .ic { width: 18px; height: 18px }
.heart[aria-pressed="true"] .ic { color: var(--accent) }
.heart-msg { max-width: 220px; padding: 6px 10px; border-radius: var(--radius-sm); font-size: 12px;
             background: var(--panel); color: var(--accent); border: 1px solid var(--line) }
.heart-invite { color: var(--ink); max-width: 240px; line-height: 1.45 }
.heart-invite a { color: var(--accent); text-decoration: underline }
.heart-x { margin-left: 4px; border: 0; background: none; color: var(--dim); cursor: pointer; font: inherit; padding: 0 2px }
.heart-x:focus-visible { outline: 2px solid var(--ink-2) }
@media (prefers-reduced-motion: reduce) { .heart { transition: none } .heart:active { transform: none } }
</style>
