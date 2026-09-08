<template>
  <div class="facets">
    <div v-for="f in facets" :key="f.id">
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
import { reactive } from 'vue'
import { FACETS } from '@/data'

defineProps({
  selected: Object,
  counts: Object
})

defineEmits(['toggle', 'clear'])

const facets = FACETS
const expanded = reactive({})

function visible(f) {
  if (f.options.length <= 6 || expanded[f.id]) return f.options
  return f.options.slice(0, 6)
}

function hidden(f) {
  return Math.max(0, f.options.length - 6)
}
</script>
