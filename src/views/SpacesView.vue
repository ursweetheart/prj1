<template>
  <main class="sp wrap">
    <header class="projects-head">
      <div>
        <h1 class="projects-title">Không gian</h1>
        <p class="projects-intro">
          Tìm không gian tương tự trong các dự án của D3 Studio: mô tả bằng lời, dùng một ảnh bạn thích,
          hoặc lọc theo phong cách, tông màu, vật liệu.
        </p>
      </div>
    </header>

    <!-- Không có máy chủ AI (bản tĩnh, máy chủ tắt): không hiện dữ liệu minh hoạ -->
    <section v-if="offline" class="sp-off">
      <p>Mục tìm không gian cần máy chủ AI, hiện chưa kết nối được.</p>
      <router-link class="pv-nav-link glow-hover" to="/du-an">Xem các dự án <span aria-hidden="true">→</span></router-link>
    </section>

    <template v-else>
      <form class="sp-search" role="search" @submit.prevent="runSearch">
        <label for="q" class="sr-only">Tìm không gian bằng mô tả</label>
        <input id="q" ref="qInput" v-model="q" class="sp-input" type="search"
               placeholder="Mô tả không gian, ví dụ: phòng ngủ ấm áp tông gỗ">
        <div class="sp-actions">
          <button class="sp-btn glow-hover" type="submit" :disabled="loading">{{ loading ? 'Đang tìm…' : 'Tìm' }}</button>
          <button class="sp-btn glow-hover" type="button" :disabled="loading" @click="photoInput.click()">Tìm bằng ảnh</button>
          <button v-if="searching" class="sp-btn is-dim" type="button" :disabled="loading" @click="resetSearch">Xóa</button>
        </div>
        <input ref="photoInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onPhotoPicked">
      </form>

      <!-- Kết quả tìm bằng chữ / ảnh -->
      <section v-if="searching" class="sp-results" aria-live="polite">
        <div class="sp-query">
          <img v-if="photoUrl && !searchError" :src="photoUrl" alt="Ảnh bạn dùng để tìm" class="sp-photo">
          <p v-if="searchError" class="sp-note" role="alert">{{ searchError }}</p>
          <p v-else-if="hits" class="sp-count">
            {{ hits.length }} không gian {{ photoUrl ? 'giống ảnh của bạn' : `gần với “${lastQuery}”` }}
          </p>
        </div>
        <div v-if="hits && hits.length" class="projects-grid">
          <SpaceTile v-for="s in hits" :key="s.id" :space="s" />
        </div>
        <p v-else-if="hits" class="sp-note">
          {{ photoUrl ? 'Chưa có không gian nào giống ảnh này.' : 'Chưa có không gian nào phù hợp mô tả này.' }}
        </p>
      </section>

      <!-- Mặc định: mọi không gian đã đăng + bộ lọc -->
      <div v-else class="browse">
        <aside aria-label="Bộ lọc">
          <div class="sp-filter-h">
            <span class="sp-label">Bộ lọc</span>
            <button v-if="activeChips.length" class="sp-btn is-dim" type="button" @click="clearAll">Bỏ hết</button>
          </div>
          <FacetPanel class="only-desk" :facets="portfolio.facets" :selected="selected" :counts="counts" :locks="locks"
                      @toggle="toggle" @clear="clear" />
          <button class="btn btn-secondary facet-drawer-btn" type="button" @click="drawer = true">
            Mở bộ lọc<span v-if="activeChips.length" class="num"> · {{ activeChips.length }}</span>
          </button>
        </aside>

        <section>
          <div class="facet-bar">
            <span class="sp-count num">{{ results.length }} không gian</span>
            <span v-if="portfolio.source === 'loading'" class="sp-note">Đang tải…</span>
            <button v-for="c in activeChips" :key="c.fid + c.vid" class="chip"
                    aria-pressed="true" type="button" @click="toggle(c.fid, c.vid)">
              {{ c.label }}<span class="x" aria-hidden="true">×</span>
              <span class="sr-only">— bỏ điều kiện này</span>
            </button>
          </div>

          <div v-if="results.length" class="projects-grid">
            <SpaceTile v-for="s in shown" :key="s.id" :space="s" />
          </div>
          <div v-if="results.length > limit" class="projects-more">
            <button type="button" class="btn btn-secondary" @click="limit += PAGE">Xem thêm</button>
          </div>

          <div v-else-if="!results.length && portfolio.source === 'api'" class="empty">
            <p>{{ portfolio.spaces.length ? 'Không có không gian nào khớp mọi điều kiện.' : 'Chưa có không gian nào được đăng.' }}</p>
            <button v-if="portfolio.spaces.length" class="sp-btn glow-hover" type="button" @click="clearAll">Bỏ hết điều kiện</button>
          </div>
        </section>
      </div>
    </template>
  </main>

  <!-- Drawer bộ lọc cho màn hẹp -->
  <div v-if="drawer" class="drawer-back" @click="drawer = false"></div>
  <aside v-if="drawer" class="drawer" role="dialog" aria-modal="true" aria-label="Bộ lọc">
    <div class="drawer-top">
      <span class="sp-label">Bộ lọc</span>
      <button class="btn btn-ghost" type="button" @click="drawer = false">Đóng</button>
    </div>
    <FacetPanel :facets="portfolio.facets" :selected="selected" :counts="counts" :locks="locks" @toggle="toggle" @clear="clear" />
    <div class="row g10" style="margin-top:auto; padding-top:18px">
      <button class="btn btn-secondary" type="button" style="flex:1" @click="clearAll">Bỏ hết</button>
      <button class="btn btn-primary" type="button" style="flex:1" @click="drawer = false">
        Xem {{ results.length }} kết quả
      </button>
    </div>
  </aside>
</template>

<script setup>
/* Mục "Không gian": tìm không gian tương tự bằng mô tả, bằng ảnh, hoặc lọc theo các chiều phân loại.
 * Logic tìm / lọc giữ nguyên của trang /cong-trinh cũ; giao diện theo lưới dự án. */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useBrowse } from '@/composables/useBrowse'
import { usePortfolio } from '@/composables/usePortfolio'
import FacetPanel from '@/components/FacetPanel.vue'
import SpaceTile from '@/components/SpaceTile.vue'
import { searchByImage, searchSpaces, toCard } from '@/api'
import { takePendingPhoto } from '@/lib/projectSpaces'

const PAGE = 24
const route = useRoute()

const portfolio = usePortfolio()
const offline = computed(() => portfolio.source === 'demo')
const { selected, results, counts, activeChips, toggle, clear, clearAll } = useBrowse(() => portfolio.spaces, () => portfolio.facets)
// a dimension no published space carries yet (loại công trình, mức đầu tư before staff fill them in) filters nothing
const locks = computed(() => portfolio.source !== 'api' ? {} : Object.fromEntries(portfolio.facets
  .filter(f => !portfolio.spaces.some(s => s.tags[f.id]?.length))
  .map(f => [f.id, 'Chưa lọc được — chưa có không gian nào được gắn nhãn này.'])))
const drawer = ref(false)

const limit = ref(PAGE)
const shown = computed(() => results.value.slice(0, limit.value))
watch(() => activeChips.value.length, () => { limit.value = PAGE })

/* Tìm bằng mô tả */
const q = ref('')
const qInput = ref(null)
const lastQuery = ref('')
const hits = ref(null)
const loading = ref(false)
const searchError = ref('')
const searching = computed(() => !!(hits.value || searchError.value || photoUrl.value))

async function runSearch() {
  const text = q.value.trim()
  if (!text) return resetSearch()
  dropPhoto()
  loading.value = true; searchError.value = ''
  try {
    hits.value = (await searchSpaces(text, 24)).map(toCard)
    lastQuery.value = text
  } catch (e) { hits.value = null; searchError.value = e.message }
  finally { loading.value = false }
}

function resetSearch() { q.value = ''; hits.value = null; searchError.value = ''; dropPhoto() }

/* Tìm bằng ảnh: ảnh chỉ gửi cho lần tìm này, ảnh thu nhỏ là object URL cục bộ */
const photoInput = ref(null)
const photoUrl = ref('')

function dropPhoto() {
  if (photoUrl.value) URL.revokeObjectURL(photoUrl.value)
  photoUrl.value = ''
}

function onPhotoPicked(e) {
  const file = e.target.files[0]
  e.target.value = '' // chọn lại cùng ảnh vẫn tìm lại
  if (file) searchPhoto(file)
}

async function searchPhoto(file) {
  dropPhoto(); q.value = ''
  photoUrl.value = URL.createObjectURL(file)
  loading.value = true; searchError.value = ''; hits.value = null
  try { hits.value = (await searchByImage(file, 24)).map(toCard) }
  catch (err) { searchError.value = err.message }
  finally { loading.value = false }
}

// đến từ dải ở trang chủ: ảnh đã chọn sẵn, hoặc ?tim=mo-ta để gõ mô tả ngay
onMounted(async () => {
  const file = takePendingPhoto()
  if (file) return searchPhoto(file)
  if (route.query.tim === 'mo-ta') { await nextTick(); qInput.value?.focus() }
})
onBeforeUnmount(dropPhoto)
</script>

<style scoped>
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap }
.only-desk { display:none }
@media (min-width: 1024px) { .only-desk { display:flex } }

/* cùng khoảng chừa cho header cố định như trang /du-an */
.sp { max-width: 1280px; padding-top: 196px; padding-bottom: clamp(48px, 7vw, 96px) }
@media (min-width: 600px)  { .sp { padding-top: 232px } }
@media (min-width: 1024px) { .sp { padding-top: 128px } }

.sp-search { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 14px 28px;
             margin-bottom: clamp(32px, 4vw, 56px) }
.sp-input { flex: 1 1 320px; min-width: 0; padding: 10px 0; border: 0; border-bottom: 1px solid var(--line);
            background: none; color: var(--ink); font: inherit; font-size: clamp(16px, 1.3vw, 19px); outline: none;
            transition: border-color .45s cubic-bezier(0.22, 1, 0.36, 1) }
.sp-input::placeholder { color: var(--faint) }
.sp-input:focus, .sp-input:focus-visible { border-bottom-color: var(--ink); outline: none; box-shadow: none }
.sp-actions { display: flex; flex-wrap: wrap; gap: 6px 22px }
.sp-btn { padding: 6px 0; border: 0; background: none; cursor: pointer; font: inherit; font-size: 14px;
          color: var(--ink); letter-spacing: 0.02em }
.sp-btn.is-dim { color: var(--faint) }
.sp-btn.is-dim:hover { color: var(--ink) }
.sp-btn[disabled] { opacity: .45; cursor: default }

.sp-query { display: flex; align-items: flex-end; gap: 18px; margin-bottom: 24px }
.sp-photo { width: 120px; aspect-ratio: 4 / 3; object-fit: cover; display: block }
.sp-count { font-size: 14px; color: var(--ink-2); letter-spacing: 0.02em; margin: 0 }
.sp-note { font-size: 14px; color: var(--faint); margin: 0 }
.sp-label { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--faint) }
.sp-filter-h { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 18px }
.sp-off { display: grid; gap: 18px; justify-items: start; color: var(--ink-2); font-size: 15px }
.sp .projects-grid { column-gap: clamp(16px, 2vw, 28px) }
@media (min-width: 1024px) { .browse .projects-grid { column-count: 3 } }
</style>
