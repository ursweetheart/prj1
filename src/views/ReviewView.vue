<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Duyệt không gian</h1>
    <p class="lead" style="margin-top:10px">AI gán nhãn ở trạng thái nháp; kiến trúc sư xác nhận trước khi đăng.</p>

    <div class="row g10" style="margin-top:24px;flex-wrap:wrap">
      <button v-for="(label, key) in STATUS_VI" :key="key" type="button" class="chip"
              :aria-pressed="String(status === key)" :class="{ 'is-on': status === key }" @click="status = key">{{ label }}</button>
    </div>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!rows.length" class="small" style="margin-top:20px">{{ loading ? 'Đang tải…' : 'Không có không gian nào ở trạng thái này.' }}</p>

    <ul class="stack" style="margin-top:20px;gap:14px;list-style:none;padding:0">
      <li v-for="r in rows" :key="r.id" class="form-ok" style="gap:16px;flex-wrap:wrap">
        <img :src="imageUrl(r.relative_path)" :alt="r.alt_text" loading="lazy"
             style="width:140px;height:100px;object-fit:cover;border-radius:var(--radius-sm)">
        <div style="flex:1;min-width:240px">
          <p class="small">{{ r.relative_path }}</p>
          <p class="small" style="margin-top:4px">{{ r.caption }}</p>
          <div class="row g10" style="margin-top:12px;flex-wrap:wrap">
            <select v-model="r.space_type" :aria-label="'Loại không gian ' + r.id">
              <option v-for="t in SPACE_TYPES" :key="t" :value="t">{{ spaceLabel(t) }}</option>
            </select>
            <select v-model="r.design_style" :aria-label="'Phong cách ' + r.id">
              <option v-for="s in STYLES" :key="s" :value="s">{{ s.replaceAll('_', ' ') }}</option>
            </select>
            <button class="btn btn-secondary" type="button" @click="save(r, false)">Lưu nhãn</button>
            <button v-if="canAdvance(r)" class="btn btn-primary" type="button" @click="save(r, true)">
              Chuyển sang «{{ STATUS_VI[NEXT_STATUS[r.review_status]] }}»
            </button>
          </div>
        </div>
      </li>
    </ul>
  </main>
</template>

<script setup>
import { ref, watch } from 'vue'
import { APPROVERS, NEXT_STATUS, SPACE_TYPES, STATUS_VI, STYLES, hasRole, imageUrl, listSpaces, reviewSpace, spaceLabel } from '@/api'

const status = ref('draft')
const rows = ref([])
const loading = ref(false)
const error = ref('')

// architects move draft -> in_review; only the lead architect approves and publishes
const canAdvance = r => r.review_status in NEXT_STATUS && (r.review_status === 'draft' || hasRole(APPROVERS))

async function load() {
  loading.value = true; error.value = ''
  try { rows.value = await listSpaces({ review_status: status.value }) }
  catch (e) { error.value = e.message; rows.value = [] }
  finally { loading.value = false }
}

async function save(r, advance) {
  error.value = ''
  try {
    await reviewSpace(r.id, { space_type: r.space_type, design_style: r.design_style, advance })
    if (advance) rows.value = rows.value.filter(x => x.id !== r.id)
  } catch (e) { error.value = e.message }
}

watch(status, load, { immediate: true })
</script>

<style scoped>
select { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 10px 12px; min-height: 42px; max-width: 100%; color-scheme: dark }
select:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring) }
</style>
