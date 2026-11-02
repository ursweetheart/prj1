<template>
  <article v-if="project" class="pv wrap">
    <header class="pv-head">
      <div>
        <p class="pv-eyebrow">{{ LOAI_NAME[project.loai] }}</p>
        <h1 class="pv-title">{{ project.name }}</h1>
      </div>
      <p v-if="project.brief" class="pv-brief">{{ project.brief }}</p>
    </header>

    <!-- Toàn bộ ảnh dự án, đúng tỉ lệ gốc: ảnh ngang trọn hàng, ảnh dọc / vuông ghép đôi -->
    <section class="pv-gallery" :aria-label="'Ảnh dự án ' + project.name">
      <div v-for="(row, r) in rows" :key="r" class="pv-row" :class="{ 'is-lone': row.lone }">
        <button v-for="item in row.items" :key="item.index" type="button" class="pv-photo"
                :style="{ '--r': item.w / item.h }"
                :aria-label="'Xem lớn ảnh ' + (item.index + 1)"
                @click="open = item.index">
          <img :src="item.src" :width="item.w" :height="item.h"
               :alt="project.name + ' — ảnh ' + (item.index + 1)"
               :loading="item.index < 2 ? 'eager' : 'lazy'" decoding="async">
        </button>
      </div>
    </section>

    <nav class="pv-nav" aria-label="Dự án khác">
      <router-link class="pv-nav-link glow-hover" :to="'/du-an/' + prev.slug">
        <span aria-hidden="true">←</span> <span class="pv-nav-label">Dự án trước</span><span class="pv-nav-name">{{ prev.name }}</span>
      </router-link>
      <router-link class="pv-nav-link is-all glow-hover" to="/#du-an">Tất cả dự án</router-link>
      <router-link class="pv-nav-link is-next glow-hover" :to="'/du-an/' + next.slug">
        <span class="pv-nav-label">Dự án tiếp</span><span class="pv-nav-name">{{ next.name }}</span> <span aria-hidden="true">→</span>
      </router-link>
    </nav>

    <Lightbox v-if="open !== null" :items="lightboxItems" :index="open"
              @close="open = null" @go="d => open = (open + d + images.length) % images.length" />
  </article>

  <section v-else class="pv wrap pv-missing">
    <h1 class="pv-title">Không tìm thấy dự án</h1>
    <p class="pv-brief">Dự án này không tồn tại hoặc đã được đổi địa chỉ.</p>
    <router-link class="pv-nav-link glow-hover" to="/#du-an">← Về danh sách dự án</router-link>
  </section>
</template>

<script setup>
/* Trang một dự án: hàng tiêu đề (loại công trình, tên, mô tả khi có) rồi toàn bộ ảnh dự án
 * theo tỉ lệ gốc (kiểu elemental.com.vn); bấm ảnh để xem toàn màn hình. */
import { computed, onBeforeUnmount, ref, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import Lightbox from '@/components/Lightbox.vue'
import { LOAI_NAME, PROJECTS_LIST, projectBySlug } from '@/data/projects'
import { galleryRows } from '@/lib/galleryRows'

const route = useRoute()
const project = computed(() => projectBySlug(route.params.slug))

const images = computed(() => (project.value ? project.value.images.map((im, index) => ({ ...im, index })) : []))
const rows = computed(() => galleryRows(images.value))
const lightboxItems = computed(() => images.value.map(im => ({ img: im.src, alt: project.value.name + ' — ảnh ' + (im.index + 1) })))

const open = ref(null) // ảnh đang xem toàn màn hình (chỉ số) hoặc null

const index = computed(() => PROJECTS_LIST.findIndex(p => p.slug === route.params.slug))
const wrap = i => (i + PROJECTS_LIST.length) % PROJECTS_LIST.length
const prev = computed(() => PROJECTS_LIST[wrap(index.value - 1)])
const next = computed(() => PROJECTS_LIST[wrap(index.value + 1)])

watch(() => route.params.slug, () => { open.value = null })

const baseTitle = document.title
watchEffect(() => {
  document.title = (project.value ? project.value.name : 'Không tìm thấy dự án') + ' — D3 Studio'
})
onBeforeUnmount(() => { document.title = baseTitle })
</script>
