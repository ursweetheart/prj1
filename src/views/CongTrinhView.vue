<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Công trình</p>
    <h1 class="h-1" style="margin-top:12px; max-width:22ch">Filtra secundum quod imaginaris</h1>
    <p class="lead" style="margin-top:16px">
      Lorem ipsum dolor sit amet, <strong>consectetur</strong> adipiscing elit. Sed do eiusmod
      tempor incididunt ut labore et dolore magna aliqua veniam.
    </p>

    <form class="row g10" style="margin-top:24px;max-width:680px" role="search" @submit.prevent="runSearch">
      <div class="field" style="flex:1">
        <label for="q" class="sr-only">Tìm không gian bằng mô tả</label>
        <input id="q" v-model="q" type="search" placeholder="Tìm bằng mô tả, ví dụ: phòng ngủ ấm áp tông gỗ">
      </div>
      <button class="btn btn-primary" type="submit" :disabled="loading">{{ loading ? 'Đang tìm…' : 'Tìm' }}</button>
      <button v-if="hits" class="btn btn-ghost" type="button" @click="resetSearch">Xóa</button>
    </form>

    <div v-if="hits || searchError" style="margin-top:clamp(28px,3.4vw,48px)" aria-live="polite">
      <p v-if="searchError" class="lead" role="alert">{{ searchError }}</p>
      <template v-else>
        <p class="small num">{{ hits.length }} không gian gần với "{{ lastQuery }}"</p>
        <div v-if="hits.length" class="mosaic" style="margin-top:16px">
          <SpaceCard v-for="s in hits" :key="s.id" :space="s" :href="'/khong-gian/' + s.apiId" />
        </div>
        <p v-else class="lead">Không tìm thấy không gian phù hợp.</p>
      </template>
    </div>

    <div v-else class="browse" style="margin-top:clamp(28px,3.4vw,48px)">
      <!-- Cột bộ lọc -->
      <aside aria-label="Bộ lọc">
        <div class="row between g10" style="margin-bottom:18px">
          <span class="h-4">Bộ lọc</span>
          <button v-if="activeChips.length" class="btn btn-ghost"
                  style="min-height:auto;padding:2px 4px;font-size:13px"
                  type="button" @click="clearAll">Bỏ hết</button>
        </div>
        <div style="display:none" class="d-desk"></div>
        <FacetPanel class="only-desk" :selected="selected" :counts="counts"
                     @toggle="toggle" @clear="clear" />
        <button class="btn btn-secondary facet-drawer-btn" type="button" @click="drawer = true">
          Mở bộ lọc<span v-if="activeChips.length" class="num"> · {{ activeChips.length }}</span>
        </button>
      </aside>

      <section>
        <div class="facet-bar">
          <span class="n num">{{ results.length }} không gian</span>
          <span class="small" v-if="!activeChips.length">Lorem ipsum condicionem</span>
          <button v-for="c in activeChips" :key="c.fid + c.vid" class="chip"
                  aria-pressed="true" type="button" @click="toggle(c.fid, c.vid)">
            {{ c.label }}<span class="x" aria-hidden="true">×</span>
            <span class="sr-only">— bỏ điều kiện này</span>
          </button>
        </div>

        <div v-if="results.length" class="mosaic">
          <SpaceCard v-for="(s, i) in results" :key="s.id" :space="s"
                     :class="wideAt(i) ? 'm-wide' : ''"
                     :ratio="wideAt(i) ? 'l32' : ''" />
        </div>

        <div v-else class="empty">
          <p class="h-3">Nullum spatium congruit omnibus condicionibus</p>
          <p class="body" style="margin:12px auto 20px; max-width:44ch">
            Lorem ipsum dolor sit amet — consectetur adipiscing elit tempor.
          </p>
          <button class="btn btn-secondary" type="button" @click="clearAll">Bỏ hết điều kiện</button>
        </div>
      </section>
    </div>
  </main>

  <!-- Drawer bộ lọc cho màn hẹp -->
  <div v-if="drawer" class="drawer-back" @click="drawer = false"></div>
  <aside v-if="drawer" class="drawer" role="dialog" aria-modal="true" aria-label="Bộ lọc">
    <div class="drawer-top">
      <span class="h-4">Bộ lọc</span>
      <button class="btn btn-ghost" type="button" @click="drawer = false">Đóng</button>
    </div>
    <FacetPanel :selected="selected" :counts="counts" @toggle="toggle" @clear="clear" />
    <div class="row g10" style="margin-top:auto; padding-top:18px">
      <button class="btn btn-secondary" type="button" style="flex:1" @click="clearAll">Bỏ hết</button>
      <button class="btn btn-primary" type="button" style="flex:1" @click="drawer = false">
        Xem {{ results.length }} kết quả
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { useBrowse } from '@/composables/useBrowse'
import FacetPanel from '@/components/FacetPanel.vue'
import SpaceCard from '@/components/SpaceCard.vue'
import { searchSpaces, toCard } from '@/api'

const { selected, results, counts, activeChips, toggle, clear, clearAll } = useBrowse()
const drawer = ref(false)
const wideAt = i => i % 7 === 0

/* Tìm bằng mô tả (AI, API thật) */
const q = ref('')
const lastQuery = ref('')
const hits = ref(null)
const loading = ref(false)
const searchError = ref('')

async function runSearch() {
  const text = q.value.trim()
  if (!text) return resetSearch()
  loading.value = true; searchError.value = ''
  try {
    hits.value = (await searchSpaces(text)).map(toCard)
    lastQuery.value = text
  } catch (e) { hits.value = null; searchError.value = e.message }
  finally { loading.value = false }
}

function resetSearch() { q.value = ''; hits.value = null; searchError.value = '' }
</script>

<style scoped>
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap }
.only-desk { display:none }
@media (min-width: 1024px) { .only-desk { display:flex } }
</style>
