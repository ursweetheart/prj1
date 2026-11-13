<template>
  <div class="hs-wrap" @keydown.esc="active = -1">
    <!-- ảnh đúng tỉ lệ gốc (không crop) để điểm neo % trùng đúng món đồ -->
    <img class="hs-img" :src="src" :alt="alt" @load="$emit('load', $event)">
    <template v-if="show">
      <button v-for="(h, i) in hotspots" :key="i" class="hs" type="button"
              :style="{ left: h.x + '%', top: h.y + '%' }"
              :aria-expanded="String(active === i)" :aria-label="'Món đồ: ' + h.label"
              @click="active = active === i ? -1 : i">{{ active === i ? '×' : '+' }}</button>
      <div v-for="(h, i) in hotspots" :key="'c' + i" v-show="active === i"
           class="hs-card" :style="cardStyle(h)">
        <b>{{ h.label }}</b>
        <button class="hs-link" type="button" @click="active = -1; $emit('similar')">
          Không gian tương tự <span aria-hidden="true">→</span>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
/* Ảnh một không gian với các món đồ AI nhận ra (đã được kiến trúc sư giữ lại).
 * Bấm "+" chỉ hiện tên món đồ và lối sang các không gian tương tự — không giá, không bán hàng. */
import { ref, watch } from 'vue'

const props = defineProps({
  src: String,
  alt: String,
  hotspots: { type: Array, default: () => [] }, // [{ x, y, label }] theo %
  show: { type: Boolean, default: true }
})
defineEmits(['similar', 'load'])

const active = ref(-1)
watch(() => props.src, () => { active.value = -1 })

function cardStyle(h) {
  const right = h.x > 58
  return {
    left: right ? 'auto' : 'min(' + h.x + '%, calc(100% - 240px))',
    right: right ? 'min(' + (100 - h.x) + '%, calc(100% - 240px))' : 'auto',
    top: h.y > 62 ? 'auto' : 'calc(' + h.y + '% + 24px)',
    bottom: h.y > 62 ? 'calc(' + (100 - h.y) + '% + 24px)' : 'auto'
  }
}
</script>
