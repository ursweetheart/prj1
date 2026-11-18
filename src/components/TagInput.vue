<template>
  <div class="ti" :class="{ 'is-busy': busy }">
    <!-- grey completion: an invisible copy of the typed text, then the rest of the best match, behind the input -->
    <div class="ti-ghost txt" aria-hidden="true"><span class="ti-typed">{{ q }}</span>{{ rest }}</div>
    <input :id="id" ref="el" class="txt ti-input" role="combobox" aria-autocomplete="both" autocomplete="off" spellcheck="false"
           :aria-label="label" :aria-expanded="String(open)" :aria-controls="id + '-lb'" :disabled="busy"
           :aria-activedescendant="open && active >= 0 ? id + '-o' + active : null" :value="q" :placeholder="label"
           @input="onInput($event.target.value)" @focus="onFocus" @keydown="onKey" @blur="onBlur">
    <ul v-if="open && rows.length" :id="id + '-lb'" class="ti-lb" role="listbox" :aria-label="label">
      <li v-for="(o, k) in rows" :id="id + '-o' + k" :key="o.v ? o.v.ma_dinh_danh : 'new'" role="option"
          :aria-selected="String(active === k)" :class="{ 'is-active': active === k, 'is-new': !o.v }"
          @mousedown.prevent="choose(o)">
        <template v-if="o.v">{{ o.v.ten }} <span v-if="o.v.so_anh != null" class="small num">{{ o.v.so_anh }}</span></template>
        <template v-else>+ Gợi ý giá trị mới «{{ o.text }}»</template>
      </li>
    </ul>
  </div>
</template>

<script setup>
/* review-tag-autocomplete: type a room type / style with suggestions from the stored values (like fish shell).
   Tab or → accepts the grey completion, ↑/↓ + Enter pick from the list, Esc closes it, leaving without a pick puts
   the saved value back. A word that names no value can be sent as a suggestion ('suggest' event). */
import { computed, ref, watch } from 'vue'
import { completion, exact, rank } from '@/lib/tagMatch'

const props = defineProps({
  modelValue: { type: String, default: '' }, // value code (ma_dinh_danh)
  values: { type: Array, default: () => [] }, // [{ ma_dinh_danh, ten, tu_dong_nghia, so_anh }]
  label: { type: String, required: true },
  id: { type: String, required: true },
  busy: { type: Boolean, default: false }, // a suggestion is being checked
  allowNew: { type: Boolean, default: true }, // offer "+ suggest a new value" for a word that names none
})
const emit = defineEmits(['update:modelValue', 'suggest'])

const el = ref(null)
const nameOf = code => props.values.find(v => v.ma_dinh_danh === code)?.ten ?? code ?? ''
const q = ref(nameOf(props.modelValue))
const open = ref(false)
const active = ref(-1)
watch(() => [props.modelValue, props.values], () => { if (document.activeElement !== el.value) q.value = nameOf(props.modelValue) })

const matches = computed(() => rank(props.values, q.value))
const rows = computed(() => {
  const list = matches.value.map(v => ({ v }))
  const text = q.value.trim()
  return props.allowNew && text && !exact(props.values, text) ? [...list, { v: null, text }] : list
})
const rest = computed(() => (open.value && active.value < 0 ? completion(matches.value[0], q.value) : ''))

function onFocus() { open.value = true; active.value = -1; el.value.select() }
function onInput(v) { q.value = v; open.value = true; active.value = -1 }
function onBlur() { open.value = false; active.value = -1; q.value = nameOf(props.modelValue) } // no pick = no change

function choose(o) {
  open.value = false; active.value = -1
  if (!o.v) { emit('suggest', o.text); return }
  q.value = o.v.ten
  emit('update:modelValue', o.v.ma_dinh_danh)
}

function onKey(e) {
  const n = rows.value.length
  const atEnd = e.target.selectionStart === q.value.length && e.target.selectionEnd === q.value.length
  if ((e.key === 'Tab' && !e.shiftKey && rest.value) || (e.key === 'ArrowRight' && atEnd && rest.value)) {
    e.preventDefault(); choose({ v: matches.value[0] })
  } else if (e.key === 'ArrowDown') {
    e.preventDefault(); open.value = true; active.value = n ? (active.value + 1) % n : -1
  } else if (e.key === 'ArrowUp') {
    e.preventDefault(); open.value = true; active.value = n ? (active.value - 1 + n) % n : -1
  } else if (e.key === 'Enter' && open.value) {
    e.preventDefault()
    const hit = exact(props.values, q.value)
    const o = active.value >= 0 ? rows.value[active.value] : hit ? { v: hit } : rows.value[0]
    if (o) choose(o)
  } else if (e.key === 'Escape' && open.value) {
    e.preventDefault(); open.value = false; active.value = -1 // keep the typed text; leaving the field restores it
  }
}
</script>

<style scoped>
.txt { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 8px 10px; min-height: 40px; max-width: 100%; color-scheme: dark; font: inherit }
.ti { position: relative; flex: 1 1 180px; min-width: 0 }
.ti-input { position: relative; width: 100%; background: transparent }
.ti-input:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring); outline: none }
.ti-ghost { position: absolute; inset: 0; color: var(--faint); white-space: pre; overflow: hidden; pointer-events: none;
  display: flex; align-items: center }
.ti-typed { visibility: hidden }
.ti-lb { position: absolute; z-index: 5; left: 0; right: 0; top: calc(100% + 4px); list-style: none; margin: 0; padding: 4px;
  background: var(--page); border: 1px solid var(--line); border-radius: var(--radius-md); max-height: 240px; overflow-y: auto }
.ti-lb li { padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer; display: flex; justify-content: space-between; gap: 8px }
.ti-lb li .small { color: var(--faint) }
.ti-lb li.is-active, .ti-lb li:hover { background: var(--line-soft) }
.ti-lb li.is-new { color: var(--accent) }
.is-busy { opacity: .6 }
</style>
