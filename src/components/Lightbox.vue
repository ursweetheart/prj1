<template>
  <div class="lb" role="dialog" aria-modal="true" aria-label="Xem ảnh lớn" @click.self="$emit('close')">
    <div class="lb-bar">
      <span class="meta num">{{ index + 1 }} / {{ items.length }}</span>
      <button class="btn btn-secondary" type="button" @click="$emit('close')">Đóng</button>
    </div>
    <img :src="items[index].img" :alt="items[index].alt">
    <button v-if="items.length > 1" class="lb-nav p" type="button"
            aria-label="Ảnh trước" @click="$emit('go', -1)">‹</button>
    <button v-if="items.length > 1" class="lb-nav n" type="button"
            aria-label="Ảnh sau" @click="$emit('go', 1)">›</button>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  items: Array,
  index: Number
})

const emit = defineEmits(['close', 'go'])

const onKey = e => {
  if (e.key === 'Escape') emit('close')
  if (e.key === 'ArrowRight') emit('go', 1)
  if (e.key === 'ArrowLeft') emit('go', -1)
}

onMounted(() => {
  document.addEventListener('keydown', onKey)
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>
