<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <router-link to="/cong-trinh" class="small">← Công trình</router-link>

    <p v-if="error" class="lead" style="margin-top:24px" role="alert">{{ error }}</p>
    <p v-else-if="!space" class="lead" style="margin-top:24px">Đang tải…</p>

    <template v-else>
      <div class="media l32 r-lg" style="margin-top:20px;max-height:70vh">
        <img :src="imageUrl(space.relative_path)" :alt="space.alt_text">
      </div>

      <p class="eyebrow" style="margin-top:28px">{{ facetLine }}</p>
      <h1 class="h-2" style="margin-top:10px">{{ spaceLabel(space.space_type) }}</h1>
      <p class="lead" style="margin-top:14px">{{ space.caption }}</p>

      <div v-if="space.materials?.length" class="row g10" style="margin-top:20px;flex-wrap:wrap">
        <span v-for="m in space.materials" :key="m" class="chip chip-static">{{ m }}</span>
      </div>

      <PaletteRow v-if="palette.length" :palette="palette" style="margin-top:24px" />

      <section style="margin-top:clamp(40px,5vw,72px)" aria-labelledby="similar-h">
        <h2 id="similar-h" class="h-3">Dự án tương tự</h2>
        <div v-if="similar.length" class="mosaic" style="margin-top:20px">
          <SpaceCard v-for="s in similar" :key="s.id" :space="s" :href="'/khong-gian/' + s.apiId" />
        </div>
        <p v-else class="small" style="margin-top:12px">Chưa có không gian tương tự.</p>
      </section>
    </template>
  </main>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { LOAI_LABEL, PC_LABEL } from '@/data'
import { getSpace, getSimilar, imageUrl, spaceLabel, toCard } from '@/api'
import PaletteRow from '@/components/PaletteRow.vue'
import SpaceCard from '@/components/SpaceCard.vue'

const route = useRoute()
const space = ref(null)
const similar = ref([])
const error = ref('')

const palette = computed(() =>
  (space.value?.palette?.palette || []).map(c => ({ hex: c.hex_code, pct: Math.round(c.percentage), name: c.hex_code })))

const facetLine = computed(() => {
  const s = space.value
  return [spaceLabel(s.space_type), PC_LABEL[toCard(s).phongcach] || s.design_style].filter(Boolean).join(' · ')
})

watch(() => route.params.id, async id => {
  space.value = null; similar.value = []; error.value = ''
  window.scrollTo(0, 0)
  try {
    const [s, sim] = await Promise.all([getSpace(id), getSimilar(id)])
    space.value = s
    similar.value = sim.map(toCard)
  } catch (e) { error.value = e.message }
}, { immediate: true })
</script>
