<template>
  <main class="wrap wrap-wide page-top tx-page">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Phân loại</h1>

    <div class="tx-tabs" role="tablist" aria-label="Phân loại" @keydown="onTabKey">
      <button v-for="t in TABS" :id="'tab-' + t.id" :key="t.id" ref="tabEls" type="button" role="tab" class="tx-tab"
              :aria-selected="String(tab === t.id)" :aria-controls="'panel-' + t.id" :tabindex="tab === t.id ? 0 : -1"
              @click="select(t.id)">{{ t.label }}</button>
    </div>

    <div v-for="t in TABS" v-show="tab === t.id" :id="'panel-' + t.id" :key="t.id" role="tabpanel"
         :aria-labelledby="'tab-' + t.id" tabindex="0" class="tx-panel">
      <template v-if="tab === t.id || seen.has(t.id)">
        <TaxonomyTree v-if="t.id === 'danh-muc'" />
        <TaxonomyCandidates v-else />
      </template>
    </div>
  </main>
</template>

<script setup>
/* /quan-tri/phan-loai (KTS trưởng, admin): "Danh mục" = the taxonomy itself (seq-15), "Đề xuất của AI" = proposed
 * dimensions waiting for review. ?tab=de-xuat opens the second tab. */
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaxonomyCandidates from '@/components/TaxonomyCandidates.vue'
import TaxonomyTree from '@/components/TaxonomyTree.vue'

const TABS = [{ id: 'danh-muc', label: 'Danh mục' }, { id: 'de-xuat', label: 'Đề xuất của AI' }]
const route = useRoute()
const router = useRouter()
const tab = computed(() => (route.query.tab === 'de-xuat' ? 'de-xuat' : 'danh-muc'))
const seen = ref(new Set([tab.value])) // a tab keeps its state once opened
const tabEls = ref([])

function select(id) {
  seen.value.add(id)
  router.replace({ query: { ...route.query, tab: id === 'danh-muc' ? undefined : id } })
}

function onTabKey(e) {
  const at = TABS.findIndex(t => t.id === tab.value)
  const to = e.key === 'ArrowRight' ? (at + 1) % TABS.length : e.key === 'ArrowLeft' ? (at - 1 + TABS.length) % TABS.length
    : e.key === 'Home' ? 0 : e.key === 'End' ? TABS.length - 1 : -1
  if (to < 0) return
  e.preventDefault()
  select(TABS[to].id)
  nextTick(() => tabEls.value[to]?.focus())
}
</script>

<style scoped>
.tx-page { padding-bottom: clamp(48px, 7vw, 96px) }
.tx-tabs { display: flex; gap: 4px; margin: 24px 0 20px; border-bottom: 1px solid var(--line) }
.tx-tab { background: none; border: 0; border-bottom: 2px solid transparent; margin-bottom: -1px; padding: 10px 14px;
          font: inherit; font-size: 15px; color: var(--dim); cursor: pointer }
.tx-tab[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); font-weight: 600 }
.tx-tab:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px }
.tx-panel:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; border-radius: 4px }
</style>
