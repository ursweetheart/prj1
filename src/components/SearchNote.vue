<template>
  <div v-if="lines.length" class="search-note" role="status">
    <p v-for="(l, i) in lines" :key="i" :class="l.cls">{{ l.text }}</p>
  </div>
</template>

<script setup>
/* search-explanations (seq-8 b6 / b13, seq-11 b4 / b12): what the search understood. Reads lastSearch, which the
 * search calls in api.js fill: the filters taken from a description, the rewording hint, an uploaded photo's style and
 * tone, or why the photo was refused. The page shows it only while a search result is shown. */
import { computed } from 'vue'
import { lastSearch } from '@/api'

const lines = computed(() => {
  const s = lastSearch, out = []
  if (s.kind === 'anh') {
    if (s.noi_that === false) out.push({ text: s.thong_bao, cls: 'is-warn' })
    else {
      const p = s.dac_diem?.phong_cach, t = s.dac_diem?.tong_mau
      const parts = [p && `phong cách ${p.ten}`, t && `tông màu ${t.ten}`].filter(Boolean)
      if (parts.length) out.push({ text: `Ảnh của bạn có vẻ thuộc ${parts.join(', ')}.` })
    }
  } else if (s.kind === 'mo_ta') {
    if (s.rang_buoc?.length) out.push({ text: 'Đã lọc: ' + s.rang_buoc.map(c => c.ten).join(' · ') })
    if (s.goi_y) out.push({ text: s.goi_y, cls: 'is-warn' })
  }
  return out
})
</script>

<style scoped>
.search-note { margin: 8px 0 16px; display: grid; gap: 4px }
.search-note p { margin: 0; font-size: 14px; line-height: 1.5; color: var(--dim) }
.search-note .is-warn { color: var(--warn) }
</style>
