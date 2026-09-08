<template>
  <div class="hs-wrap">
    <div class="media" :class="space.ratio">
      <img :src="space.img" :alt="space.projectName + ' — ' + space.space">
    </div>
    <button v-for="(h, i) in space.hotspots" :key="i" class="hs" type="button"
            :style="{ left: h.x + '%', top: h.y + '%' }"
            :aria-expanded="String(active === i)" :aria-label="'Xem món đồ: ' + h.label"
            @click="active = active === i ? -1 : i">{{ active === i ? '×' : '+' }}</button>
    <div v-for="(h, i) in space.hotspots" :key="'c' + i" v-show="active === i"
         class="hs-card" :style="cardStyle(h)">
      <span class="meta" style="font-size:11px">{{ h.kind }}</span>
      <b>{{ h.label }}</b>
      <span class="small">Giá tham khảo: {{ h.price || '—' }}</span>
      <router-link class="btn btn-secondary" style="min-height:38px;padding:8px 12px"
         :to="'/cong-trinh#phongcach=' + space.phongcach">Xem không gian tương tự</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  space: Object
})

const active = ref(-1)

function cardStyle(h) {
  const right = h.x > 58
  return {
    left: right ? 'auto' : 'min(' + h.x + '%, calc(100% - 280px))',
    right: right ? 'min(' + (100 - h.x) + '%, calc(100% - 280px))' : 'auto',
    top: h.y > 62 ? 'auto' : 'calc(' + h.y + '% + 26px)',
    bottom: h.y > 62 ? 'calc(' + (100 - h.y) + '% + 26px)' : 'auto'
  }
}
</script>
