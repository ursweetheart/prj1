<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Công trình</p>
    <h1 class="h-1" style="margin-top:12px; max-width:22ch">Filtra secundum quod imaginaris</h1>
    <p class="lead" style="margin-top:16px">
      Lorem ipsum dolor sit amet, <strong>consectetur</strong> adipiscing elit. Sed do eiusmod
      tempor incididunt ut labore et dolore magna aliqua veniam.
    </p>

    <div class="browse" style="margin-top:clamp(28px,3.4vw,48px)">
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

const { selected, results, counts, activeChips, toggle, clear, clearAll } = useBrowse()
const drawer = ref(false)
const wideAt = i => i % 7 === 0
</script>

<style scoped>
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap }
.only-desk { display:none }
@media (min-width: 1024px) { .only-desk { display:flex } }
</style>
