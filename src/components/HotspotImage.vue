<template>
  <div class="hs-wrap" @keydown.esc="active = -1">
    <!-- ảnh đúng tỉ lệ gốc (không crop) để điểm neo % trùng đúng món đồ -->
    <img class="hs-img" :src="src" :alt="alt" @load="$emit('load', $event)">
    <template v-if="show">
      <button v-for="(h, i) in hotspots" :key="i" class="hs" type="button"
              :style="{ left: h.x + '%', top: h.y + '%' }"
              :aria-expanded="String(active === i)" :aria-label="'Món đồ: ' + h.label"
              @click="toggle(i)"><Icon name="plus" /></button>
      <div v-for="(h, i) in hotspots" :key="'c' + i" v-show="active === i"
           class="hs-card" :style="cardStyle(h)">
        <b>{{ h.label }}</b>
        <button v-if="h.itemId" class="hs-link" type="button" @click="active = -1; $emit('item', h)">
          Không gian có món đồ này <span aria-hidden="true">→</span>
        </button>
        <button v-else class="hs-link" type="button" @click="active = -1; $emit('similar')">
          Không gian tương tự <span aria-hidden="true">→</span>
        </button>
        <router-link v-if="h.service" class="hs-service" :to="{ path: '/dich-vu', hash: '#' + slug(h.service) }">
          {{ h.service }} <span aria-hidden="true">→</span>
        </router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import Icon from '@/components/Icon.vue'
/* Ảnh một không gian với các món đồ (AI nhận ra hoặc kiến trúc sư đặt tay).
 * Bấm "+" hiện tên món đồ, lối sang các không gian có cùng món đồ (hoặc tương tự) và một dòng nhỏ tới gói dịch vụ
 * liên quan ở /dich-vu (change visitor-services-hotspots) — không giá, không nút mua. */
import { ref, watch } from 'vue'
import { slug } from '@/lib/slug'

const props = defineProps({
  src: String,
  alt: String,
  hotspots: { type: Array, default: () => [] }, // [{ x, y, label, itemId, service }] theo %
  show: { type: Boolean, default: true }
})
const emit = defineEmits(['similar', 'item', 'open', 'load'])

const active = ref(-1)
const toggle = i => {
  active.value = active.value === i ? -1 : i
  if (active.value === i) emit('open', props.hotspots[i]) // behaviour-events: bam_hotspot
}
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
