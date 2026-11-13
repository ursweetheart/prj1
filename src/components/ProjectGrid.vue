<template>
  <section id="du-an" class="sec projects wrap">
    <header class="projects-head">
      <div>
        <h2 class="projects-title">Dự án</h2>
        <p class="projects-intro">
          Những không gian D3 Studio đã thiết kế và thi công, từ căn hộ, nhà phố đến không gian thương mại.
        </p>
      </div>
      <nav class="projects-tabs" aria-label="Lọc theo loại công trình">
        <button v-for="f in tabs" :key="f.id" type="button" class="projects-tab"
                :aria-pressed="String(f.id === current)" @click="select(f.id)">
          {{ f.label }}
        </button>
      </nav>
    </header>

    <div class="projects-grid">
      <router-link v-for="p in shown" :key="p.slug" class="project" :to="'/du-an/' + p.slug">
        <div class="project-img">
          <img :src="p.cover" :width="p.images[0].w" :height="p.images[0].h" alt="" loading="lazy" decoding="async">
        </div>
        <h3 class="project-name">{{ p.name }}</h3>
        <p class="project-meta">{{ LOAI_NAME[p.loai] }}<template v-if="p.year"> · {{ p.year }}</template></p>
      </router-link>
    </div>

    <div v-if="matching.length > limit" class="projects-more">
      <button type="button" class="btn btn-secondary" @click="limit += PAGE">Xem thêm</button>
    </div>
  </section>
</template>

<script>
// Số dự án đã mở bằng "Xem thêm", nhớ theo trang + tab, để bấm Back từ trang dự án
// thì lưới vẫn dài như cũ (và trình duyệt cuộn về đúng chỗ). F5 thì về lại 9.
const shownCount = new Map()
</script>

<script setup>
/* Lưới dự án trang chủ (theo bố cục elemental.com.vn): tab lọc theo nhóm công trình,
 * masonry giữ tỉ lệ ảnh gốc, 9 dự án đầu rồi "Xem thêm". Bộ lọc lưu ở #loai=… */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PROJECT_FILTERS, PROJECTS_LIST, LOAI_NAME } from '@/data/projects'

const PAGE = 9

const route = useRoute()
const router = useRouter()

const inGroup = (p, f) => !f.loai || f.loai.includes(p.loai)

// Chỉ hiện tab có ít nhất một dự án ("Tất cả" luôn hiện)
const tabs = computed(() => PROJECT_FILTERS.filter(f => !f.loai || PROJECTS_LIST.some(p => inGroup(p, f))))

const fromHash = hash => {
  const id = new URLSearchParams((hash || '').replace(/^#/, '')).get('loai')
  return tabs.value.some(f => f.id === id) ? id : 'all'
}

const current = ref(fromHash(route.hash))
const key = () => route.path + '|' + current.value
const limit = ref(shownCount.get(key()) || PAGE)

watch(() => route.hash, h => { current.value = fromHash(h) })
watch(current, () => { limit.value = shownCount.get(key()) || PAGE })
watch(limit, n => { shownCount.set(key(), n) })

function select(id) {
  current.value = id
  router.replace({ hash: id === 'all' ? '' : '#loai=' + id })
}

const matching = computed(() => {
  const f = tabs.value.find(t => t.id === current.value) || tabs.value[0]
  return PROJECTS_LIST.filter(p => inGroup(p, f))
})
const shown = computed(() => matching.value.slice(0, limit.value))
</script>
