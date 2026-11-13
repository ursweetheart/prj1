<template>
  <article class="pv wrap sv">
    <p v-if="error" class="pv-brief" role="alert">{{ error }}</p>
    <p v-else-if="!space" class="pv-brief">Đang tải…</p>

    <template v-else>
      <nav class="sv-top" aria-label="Trong dự án">
        <router-link v-if="project" class="pv-nav-link glow-hover" :to="projectPhotoHref(space.relative_path)">
          <span aria-hidden="true">←</span> {{ project.name }}<span v-if="photoNo" class="sv-dim"> · ảnh {{ photoNo }}</span>
        </router-link>
        <router-link v-else class="pv-nav-link glow-hover" to="/khong-gian"><span aria-hidden="true">←</span> Không gian</router-link>
        <div v-if="siblings.length > 1" class="sv-step">
          <router-link class="pv-nav-link glow-hover" :to="'/khong-gian/' + step(-1).id" aria-label="Không gian trước">‹</router-link>
          <span class="sv-dim num">{{ pos + 1 }} / {{ siblings.length }}</span>
          <router-link class="pv-nav-link glow-hover" :to="'/khong-gian/' + step(1).id" aria-label="Không gian tiếp">›</router-link>
        </div>
      </nav>

      <header class="pv-head">
        <div>
          <p class="pv-eyebrow">{{ eyebrow }}</p>
          <h1 class="pv-title">{{ title }}</h1>
        </div>
        <p v-if="space.caption" class="pv-brief">{{ space.caption }}</p>
      </header>

      <div class="sv-body">
        <div class="sv-photo" :style="ratio ? { '--r': ratio } : null">
          <HotspotImage :src="imageUrl(space.relative_path)" :alt="space.alt_text || title"
                        :hotspots="hotspots" :show="showSpots"
                        @similar="toSimilar" @load="onLoad" />
        </div>

        <aside v-if="hotspots.length || space.materials?.length || palette.length" class="sv-info">
          <div v-if="hotspots.length">
            <p class="sv-label">Món đồ trong ảnh</p>
            <button class="sv-toggle" type="button" :aria-pressed="String(showSpots)" @click="showSpots = !showSpots">
              {{ showSpots ? 'Ẩn điểm đánh dấu' : 'Hiện điểm đánh dấu' }} ({{ hotspots.length }})
            </button>
          </div>
          <div v-if="space.materials?.length">
            <p class="sv-label">Vật liệu</p>
            <div class="sv-chips">
              <span v-for="m in space.materials" :key="m" class="chip chip-static">{{ m }}</span>
            </div>
          </div>
          <div v-if="palette.length">
            <p class="sv-label">Bảng màu</p>
            <PaletteRow :palette="palette" />
          </div>
        </aside>
      </div>

      <section v-if="similar.length" id="tuong-tu" ref="similarEl" class="sv-similar" aria-labelledby="similar-h">
        <h2 id="similar-h" class="projects-title">Không gian tương tự</h2>
        <div class="projects-grid">
          <SpaceTile v-for="s in similar" :key="s.id" :space="s" />
        </div>
      </section>
    </template>
  </article>
</template>

<script setup>
/* Một không gian (một ảnh) với phần AI đọc được: món đồ, mô tả, vật liệu, bảng màu, không gian tương tự.
 * Cùng ngôn ngữ thiết kế với trang dự án; ‹ › đi qua các ảnh đã đăng khác của cùng dự án. */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { PC_LABEL } from '@/data'
import { projectBySlug } from '@/data/projects'
import { STAFF, getSimilar, getSpace, hasRole, hotspotsOf, imageUrl, spaceLabel, toCard, trackView } from '@/api'
import { fileOf, loadProjectSpaces, projectPhotoHref, slugOf } from '@/lib/projectSpaces'
import HotspotImage from '@/components/HotspotImage.vue'
import PaletteRow from '@/components/PaletteRow.vue'
import SpaceTile from '@/components/SpaceTile.vue'

const route = useRoute()
const space = ref(null)
const similar = ref([])
const siblings = ref([]) // các không gian đã đăng cùng dự án, theo tên file
const error = ref('')
const showSpots = ref(true)
const ratio = ref(0)
const similarEl = ref(null)

const project = computed(() => space.value && projectBySlug(slugOf(space.value.relative_path)))
const card = computed(() => toCard(space.value))
const title = computed(() => project.value?.name || card.value.projectName)
const eyebrow = computed(() => [spaceLabel(space.value.space_type), PC_LABEL[card.value.phongcach]].filter(Boolean).join(' · '))
const hotspots = computed(() => hotspotsOf(space.value))
const palette = computed(() =>
  (space.value?.palette?.palette || []).map(c => ({ hex: c.hex_code, pct: Math.round(c.percentage), name: c.hex_code })))

// số thứ tự ảnh trong trang dự án (theo thứ tự file, như lưới ảnh dự án)
const photoNo = computed(() => {
  const i = project.value?.images.findIndex(im => im.file === fileOf(space.value.relative_path))
  return i >= 0 ? i + 1 : 0
})
const pos = computed(() => siblings.value.findIndex(s => s.id === space.value.id))
const step = d => siblings.value[(pos.value + d + siblings.value.length) % siblings.value.length]

const onLoad = e => { ratio.value = e.target.naturalWidth / e.target.naturalHeight }
const toSimilar = () => similarEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })

watch(() => route.params.id, async id => {
  space.value = null; similar.value = []; siblings.value = []; error.value = ''; ratio.value = 0
  window.scrollTo(0, 0)
  try {
    const [s, sim] = await Promise.all([getSpace(id), getSimilar(id)])
    space.value = s
    similar.value = sim.map(toCard)
    if (s.review_status === 'published' && !hasRole(STAFF)) trackView(s.id) // staff browsing is not demand
    const all = await loadProjectSpaces(slugOf(s.relative_path))
    if (String(route.params.id) === String(s.id)) siblings.value = all ? [...all.values()] : []
  } catch (e) { error.value = e.message === 'Không tìm thấy dữ liệu này.' ? 'Không tìm thấy không gian.' : e.message }
}, { immediate: true })
</script>

<style scoped>
.sv-top { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: clamp(20px, 3vw, 36px) }
.sv-step { display: inline-flex; align-items: center; gap: 14px }
.sv-step .pv-nav-link { font-size: 22px; line-height: 1; padding: 2px 6px }
.sv-dim { color: var(--faint); font-size: 13px }
.sv-body { display: grid; gap: clamp(20px, 3vw, 40px); align-items: start }
@media (min-width: 1024px) { .sv-body { grid-template-columns: minmax(0, 1fr) 260px } }
/* ảnh dọc không cao quá màn hình: rộng tối đa = 78vh × tỉ lệ */
.sv-photo { width: 100%; max-width: calc(78vh * var(--r, 1.5)); margin-inline: auto }
.sv-photo :deep(.hs-img) { display: block; width: 100%; height: auto }
.sv-info { display: grid; gap: 26px }
.sv-label { margin: 0 0 10px; font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--faint) }
.sv-chips { display: flex; flex-wrap: wrap; gap: 6px }
.sv-toggle { padding: 0; border: 0; background: none; cursor: pointer; font: inherit; font-size: 14px; color: var(--ink-2) }
.sv-toggle:hover { color: var(--ink) }
.sv-similar { margin-top: clamp(56px, 7vw, 96px); scroll-margin-top: 110px }
.sv-similar .projects-title { margin-bottom: clamp(20px, 3vw, 32px) }
</style>
