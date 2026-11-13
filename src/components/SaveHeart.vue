<template>
  <span class="heart-wrap" :class="{ 'is-labelled': labelled, 'is-overlay': overlay }">
    <button class="heart" type="button" :aria-pressed="String(saved)"
            :aria-label="saved ? 'Bỏ khỏi bộ sưu tập' : 'Lưu vào bộ sưu tập'"
            :title="saved ? 'Bỏ khỏi bộ sưu tập' : 'Lưu vào bộ sưu tập'"
            @click.prevent.stop="onClick">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 20.5s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.7c0 5.6-7.5 10.2-7.5 10.2z"/>
      </svg>
      <span v-if="labelled">{{ saved ? 'Đã lưu' : 'Lưu' }}</span>
    </button>
    <span v-if="message" class="heart-msg" role="alert">{{ message }}</span>
  </span>
</template>

<script setup>
/* Trái tim lưu một không gian vào "Bộ sưu tập" (UC07). Không cần tài khoản: lib/collection.js giữ trong trình duyệt
 * cho đến khi khách đăng nhập. overlay: đặt ở góc ảnh của thẻ; labelled: kèm chữ, dùng ở trang không gian. */
import { computed, ref } from 'vue'
import { collection, has, toggle } from '@/lib/collection'

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
}
</script>

<style scoped>
.heart-wrap { display: inline-flex; flex-direction: column; align-items: flex-end; gap: 6px }
.heart-wrap.is-overlay { position: absolute; top: 10px; right: 10px; z-index: 2 }
.heart { display: inline-flex; align-items: center; gap: 8px; min-width: 40px; min-height: 40px; padding: 0 10px;
         justify-content: center; border: 1px solid var(--line); border-radius: var(--radius-pill);
         background: color-mix(in oklab, var(--fg, #111) 62%, transparent); color: var(--ink); cursor: pointer;
         font: inherit; font-size: 14px; backdrop-filter: blur(6px);
         transition: border-color var(--motion-fast, .15s) ease, transform var(--motion-fast, .15s) ease }
.heart:hover { border-color: var(--ink-2) }
.heart:focus-visible { outline: 2px solid var(--ink-2); outline-offset: 2px }
.heart:active { transform: scale(.94) }
.heart svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.7 }
.heart[aria-pressed="true"] svg { fill: var(--accent); stroke: var(--accent) }
.heart-msg { max-width: 220px; padding: 6px 10px; border-radius: var(--radius-sm); font-size: 12px;
             background: var(--panel); color: var(--accent); border: 1px solid var(--line) }
@media (prefers-reduced-motion: reduce) { .heart { transition: none } .heart:active { transform: none } }
</style>
