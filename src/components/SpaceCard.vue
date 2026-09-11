<template>
  <article class="pcard" :class="{ tall }">
    <div style="position:relative">
      <router-link :to="href" :aria-label="space.projectName + ' — ' + space.space">
        <div class="media" :class="ratio || space.ratio">
          <img :src="imageUrl" :alt="space.projectName + ' — ' + space.space" loading="lazy">
        </div>
      </router-link>
      <button class="pcard-save" type="button"
              :aria-pressed="String(moodboard.has(space.id))"
              :aria-label="moodboard.has(space.id) ? 'Bỏ lưu không gian này' : 'Lưu vào moodboard'"
              @click="moodboard.toggle(space.id)">
        <svg viewBox="0 0 24 24" :fill="moodboard.has(space.id) ? 'currentColor' : 'none'"
             stroke="currentColor" stroke-width="1.7" aria-hidden="true">
          <path d="M12 20s-7-4.4-7-9.4A4.1 4.1 0 0 1 12 7a4.1 4.1 0 0 1 7 3.6c0 5-7 9.4-7 9.4z"/>
        </svg>
      </button>
    </div>
    <router-link class="pcard-cap" :to="href">
      <span class="pcard-name">{{ space.projectName }} — {{ space.space }}</span>
      <span class="pcard-facets">{{ facetLine }}</span>
    </router-link>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { LOAI_LABEL, KG_LABEL, PC_LABEL } from '@/data'
import { useMoodboard } from '@/composables/useMoodboard'

const props = defineProps({
  space: Object,
  tall: Boolean,
  ratio: { type: String, default: '' }
})

const moodboard = useMoodboard()

const facetLine = computed(() => [
  LOAI_LABEL[props.space.loai],
  KG_LABEL[props.space.khonggian],
  PC_LABEL[props.space.phongcach]
].filter(Boolean).join(' · '))

const href = computed(() =>
  '/cong-trinh-chi-tiet#' + props.space.projectSlug + '/' + props.space.id)

const imageUrl = computed(() => {
  const imgPath = props.space.img.startsWith('/') ? props.space.img.slice(1) : props.space.img
  return import.meta.env.BASE_URL + imgPath
})
</script>
