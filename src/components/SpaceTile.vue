<template>
  <!-- the heart sits beside the link, not inside it: a button inside a link is invalid HTML -->
  <div class="space-tile-wrap">
    <router-link class="project space-tile" :to="'/khong-gian/' + space.apiId">
      <div class="project-img">
        <!-- srcset and sizes before src: Vue sets attributes in order, and a src set first starts loading the original -->
        <img :srcset="space.srcset || null" sizes="(max-width: 640px) 50vw, (max-width: 1100px) 33vw, 25vw" :src="space.img"
             :alt="name + ' — ' + space.space" loading="lazy" decoding="async">
      </div>
      <h3 class="project-name">{{ name }}</h3>
      <p class="project-meta">{{ meta }}</p>
      <p v-if="space.why?.length" class="tile-why">{{ space.why.join(' · ') }}</p>
    </router-link>
    <SaveHeart :space-id="space.apiId" overlay />
  </div>
</template>

<script setup>
/* Một không gian (một ảnh) trong mục "Không gian": cùng dáng thẻ với lưới dự án */
import { computed } from 'vue'
import SaveHeart from '@/components/SaveHeart.vue'
import { PC_LABEL } from '@/data'
import { projectBySlug } from '@/data/projects'
import { slugOf } from '@/lib/projectSpaces'

const props = defineProps({ space: Object })

// tên dự án thật nếu ảnh thuộc một dự án trên web, không thì tên thư mục
const name = computed(() => (props.space.path && projectBySlug(slugOf(props.space.path))?.name) || props.space.projectName)
const meta = computed(() => [props.space.space, PC_LABEL[props.space.phongcach]].filter(Boolean).join(' · '))
</script>

<style scoped>
/* the wrapper takes the card's place in the masonry columns; the link keeps its hover / focus styles */
.space-tile-wrap { position: relative; break-inside: avoid; margin: 0 0 clamp(28px, 3vw, 40px) }
.space-tile-wrap > .project { margin: 0 }
.tile-why { margin: 4px 0 0; font-size: 12.5px; line-height: 1.45; color: var(--dim) } /* search-explanations */
</style>
