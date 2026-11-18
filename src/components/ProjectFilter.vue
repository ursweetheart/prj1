<template>
  <section class="pf" aria-label="Lọc dự án">
    <div class="pf-bar">
      <div class="field">
        <label :for="uid + '-sort'">Sắp xếp</label>
        <select :id="uid + '-sort'" v-model="sort" class="pf-input">
          <option value="moi_nhat">Mới đăng nhất</option>
          <option value="dien_tich">Diện tích lớn nhất</option>
          <option value="xem_nhieu">Xem nhiều nhất (30 ngày)</option>
        </select>
      </div>
      <fieldset class="pf-area">
        <legend>Diện tích (m²)</legend>
        <label class="sr-only" :for="uid + '-from'">Từ</label>
        <input :id="uid + '-from'" v-model.lazy="from" class="pf-input" type="number" min="0" inputmode="numeric" placeholder="Từ">
        <span aria-hidden="true">–</span>
        <label class="sr-only" :for="uid + '-to'">Đến</label>
        <input :id="uid + '-to'" v-model.lazy="to" class="pf-input" type="number" min="0" inputmode="numeric" placeholder="Đến">
      </fieldset>
    </div>

    <div v-for="dim in DIMS" :key="dim.id" class="pf-dim">
      <p class="meta" :id="uid + dim.id">{{ dim.label }}</p>
      <div class="pf-opts" role="group" :aria-labelledby="uid + dim.id">
        <button v-for="v in data?.gia_tri?.[dim.id] || []" :key="v.ma" type="button" class="chip"
                :aria-pressed="String(on(dim.id, v.ma))" @click="toggle(dim.id, v.ma)">
          {{ v.ten }} <span class="facet-count">{{ data?.dem?.[dim.id]?.[v.ma] ?? 0 }}</span>
        </button>
      </div>
    </div>

    <p class="small pf-total" role="status">
      <template v-if="loading">Đang lọc…</template>
      <template v-else-if="error">{{ error }}</template>
      <template v-else-if="data">{{ data.tong }} dự án</template>
    </p>
    <p v-if="data && !data.tong && data.noi_long" class="small">
      Không có dự án nào khớp mọi điều kiện.
      <button class="btn btn-ghost" type="button" @click="loosen">Bỏ lọc {{ data.noi_long.ten }}: {{ data.noi_long.so_du_an }} dự án</button>
    </p>
  </section>
</template>

<script setup>
/* seq-10 / BFD 1.1-1.2 (search-explanations): filter published projects by style, building type, investment level and
 * area, with counts per value, a loosening suggestion and sorting. Emits 'results' ({tong, du_an, ...}) for the page
 * that shows the projects. Not placed on any page yet: /du-an belongs to its owner, who decides where it goes. */
import { reactive, ref, watch } from 'vue'
import { filterProjects } from '@/api'

const emit = defineEmits(['results'])
const DIMS = [{ id: 'phong_cach', label: 'Phong cách' }, { id: 'loai_cong_trinh', label: 'Loại công trình' },
  { id: 'muc_dau_tu', label: 'Mức đầu tư' }]
const uid = 'pf-' + Math.random().toString(36).slice(2, 8)
const sel = reactive({ phong_cach: [], loai_cong_trinh: [], muc_dau_tu: [] })
const from = ref(''), to = ref(''), sort = ref('moi_nhat')
const data = ref(null), loading = ref(false), error = ref('')

const on = (dim, v) => sel[dim].includes(v)
function toggle(dim, v) {
  const i = sel[dim].indexOf(v)
  if (i < 0) sel[dim].push(v); else sel[dim].splice(i, 1)
}
function loosen() {
  const d = data.value.noi_long.chieu
  if (d === 'dien_tich') { from.value = ''; to.value = '' } else sel[d] = []
}
async function load() {
  loading.value = true; error.value = ''
  try {
    data.value = await filterProjects(sel, [from.value, to.value], sort.value)
    emit('results', data.value)
  } catch (e) { error.value = 'Chưa lọc được: ' + e.message }
  finally { loading.value = false }
}
watch([sel, from, to, sort], load, { deep: true, immediate: true })
</script>

<style scoped>
.pf { display: grid; gap: 16px }
.pf-bar { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: flex-end }
.pf-area { border: 0; padding: 0; margin: 0; display: flex; align-items: center; gap: 8px }
.pf-area legend { font-size: 13px; color: var(--dim); margin-bottom: 4px; padding: 0 }
.pf-input { font: inherit; padding: 8px 10px; min-height: 40px; max-width: 100%; background: var(--panel); color: var(--ink);
  border: 1px solid var(--line); border-radius: var(--radius-md); color-scheme: dark }
.pf-area .pf-input { width: 6.5em }
.pf-input:focus-visible { box-shadow: var(--focus-ring); outline: none; border-color: var(--accent) }
.pf-opts { display: flex; flex-wrap: wrap; gap: 8px }
.pf-dim .meta { margin: 0 0 8px }
.pf-total { margin: 0 }
</style>
