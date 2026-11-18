<template>
  <select class="hs" :value="mode" :aria-label="'Trang chủ: ' + name" @change="$emit('change', value, $event.target.value, name)">
    <option value="tu_dong">Trang chủ: tự động</option>
    <option value="uu_tien">Ưu tiên trên trang chủ</option>
    <option value="an">Ẩn khỏi trang chủ</option>
  </select>
</template>

<script setup>
/* act-3: one value's homepage setting on the trend dashboard (tracking-pipeline) */
defineProps({ value: { type: String, required: true }, name: { type: String, required: true }, mode: { type: String, default: 'tu_dong' } })
defineEmits(['change'])
</script>

<style scoped>
.hs { font: inherit; font-size: 12px; padding: 2px 6px; min-height: 28px; max-width: 100%; color: var(--dim); background: var(--panel);
      border: 1px solid var(--line); border-radius: var(--radius-sm); color-scheme: dark }
.hs:focus-visible { box-shadow: var(--focus-ring); outline: none; border-color: var(--accent) }
</style>
