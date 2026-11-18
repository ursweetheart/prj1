<template>
  <div class="facets">
    <div class="field facet-sort"><!-- BFD 1.2: sort the results (search-explanations) -->
      <label :for="sortId" class="meta">Sắp xếp</label>
      <select :id="sortId" v-model="browseSort.key" class="sort-select">
        <option v-for="s in SORTS" :key="s.id" :value="s.id">{{ s.label }}</option>
      </select>
    </div>
    <div v-for="f in shown" :key="f.id">
      <div class="facet-h">
        <span class="meta">{{ f.label }}</span>
        <button v-if="!f.locked && selected[f.id] && selected[f.id].length"
                class="btn btn-ghost" style="min-height:auto;padding:2px 4px;font-size:13px"
                type="button" @click="$emit('clear', f.id)">Bỏ chọn</button>
      </div>
      <p v-if="f.locked" class="field-help" style="margin-bottom:8px">{{ f.locked }}</p>
      <div class="facet-opts">
        <button v-for="o in visible(f)" :key="o.id" class="chip" type="button"
                :disabled="!!f.locked"
                :aria-pressed="String(!f.locked && selected[f.id] && selected[f.id].includes(o.id))"
                @click="!f.locked && $emit('toggle', f.id, o.id)">
          {{ o.label }}
          <span v-if="!f.locked" class="facet-count">{{ counts[f.id] ? (counts[f.id][o.id] || 0) : 0 }}</span>
        </button>
        <button v-if="hidden(f) && !expanded[f.id]" class="btn btn-ghost"
                style="min-height:38px;font-size:13px" type="button"
                @click="expanded[f.id] = true">+ {{ hidden(f) }} nữa</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { browseSort, SORTS } from '@/composables/useBrowse'

const sortId = 'sort-' + Math.random().toString(36).slice(2, 8) // the panel is shown twice (desktop, drawer)

const props = defineProps({
  facets: Array,
  selected: Object,
  counts: Object,
  locks: { type: Object, default: () => ({}) } // facet id -> why it cannot be filtered with the current data
})

defineEmits(['toggle', 'clear'])

const shown = computed(() => props.facets.map(f => ({ ...f, locked: props.locks[f.id] || f.locked })))
const expanded = reactive({})

function visible(f) {
  if (f.options.length <= 6 || expanded[f.id]) return f.options
  return f.options.slice(0, 6)
}

function hidden(f) {
  return Math.max(0, f.options.length - 6)
}
</script>

<style scoped>
.facet-sort { margin-bottom: 18px }
.sort-select { font: inherit; padding: 8px 10px; min-height: 40px; width: 100%; background: var(--panel); color: var(--ink);
  border: 1px solid var(--line); border-radius: var(--radius-md); color-scheme: dark }
.sort-select:focus-visible { box-shadow: var(--focus-ring); outline: none; border-color: var(--accent) }
</style>
