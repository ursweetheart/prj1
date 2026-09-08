<template>
  <div class="ba" ref="el" :style="{ '--pos': pos + '%' }"
       @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up">
    <img v-if="real" :src="real" :alt="alt + ' — ảnh thi công thực tế'">
    <div v-else class="panel" style="position:absolute;inset:0;display:grid;place-items:center;
         border-radius:0;text-align:center;padding:24px">
      <p class="small" style="max-width:24ch">Lorem ipsum dolor sit amet consectetur.</p>
    </div>
    <img class="ba-top" :src="concept" :alt="alt + ' — phối cảnh concept'">
    <span class="ba-tag l">Concept</span>
    <span class="ba-tag r">Thực tế</span>
    <div class="ba-handle">
      <button class="ba-knob" type="button" role="slider" tabindex="0"
              aria-label="Kéo để so sánh concept và thực tế"
              aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round(pos)"
              @keydown="key">↔</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  concept: String,
  real: { type: String, default: '' },
  alt: String
})

const pos = ref(56)
const el = ref(null)
let dragging = false

const set = clientX => {
  if (!el.value) return
  const r = el.value.getBoundingClientRect()
  pos.value = Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100))
}

const down = e => { dragging = true; set(e.clientX); el.value.setPointerCapture(e.pointerId) }
const move = e => { if (dragging) set(e.clientX) }
const up = () => { dragging = false }
const key = e => {
  if (e.key === 'ArrowLeft') pos.value = Math.max(0, pos.value - 4)
  if (e.key === 'ArrowRight') pos.value = Math.min(100, pos.value + 4)
}
</script>
