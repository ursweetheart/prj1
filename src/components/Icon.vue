<template>
  <!-- One icon set for the whole site: 24px grid, 1.5 hairline stroke, round caps, currentColor.
       Decorative by default; give the button an aria-label, not the icon. -->
  <svg class="ic" :class="'ic-' + name" viewBox="0 0 24 24" :width="size" :height="size"
       :fill="filled ? 'currentColor' : 'none'" stroke="currentColor" aria-hidden="true" focusable="false">
    <path v-for="(d, i) in PATHS[name]" :key="i" :d="d" />
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  filled: { type: Boolean, default: false } // heart when saved
})
const PATHS = {
  'chevron-left': ['M15 5l-7 7 7 7'],
  'chevron-right': ['M9 5l7 7-7 7'],
  'arrow-right': ['M4 12h16', 'M14 6l6 6-6 6'],
  'arrow-left': ['M20 12H4', 'M10 6l-6 6 6 6'],
  'arrow-down': ['M12 4v16', 'M6 14l6 6 6-6'],
  'arrow-up': ['M12 20V4', 'M6 10l6-6 6 6'],
  'arrow-up-right': ['M7 17L17 7', 'M8 7h9v9'],
  close: ['M6 6l12 12', 'M18 6L6 18'],
  plus: ['M12 5v14', 'M5 12h14'],
  heart: ['M12 20s-7.2-4.5-7.2-9.8A4.2 4.2 0 0 1 12 7.4a4.2 4.2 0 0 1 7.2 2.8c0 5.3-7.2 9.8-7.2 9.8z']
}
</script>
