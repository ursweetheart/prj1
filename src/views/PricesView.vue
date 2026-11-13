<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Đơn giá ước tính</h1>
    <p class="lead" style="margin-top:10px">
      Khoảng giá theo m² mà trang <router-link to="/uoc-tinh">Ước tính chi phí</router-link> dùng. Ô có dấu
      <span class="chip chip-static pr-chip">Mẫu</span> là giá mẫu tham khảo, chưa phải giá của D3: sửa và lưu để thay.
    </p>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="small" style="margin-top:20px">Đang tải…</p>

    <template v-else>
      <div class="row g6 pr-tabs" role="group" aria-label="Loại nhà">
        <button v-for="h in HOUSES" :key="h.v" type="button" class="chip" :aria-pressed="String(house === h.v)"
                @click="house = h.v">{{ h.t }}<span v-if="sampleCount(h.v)" class="pr-count"> · {{ sampleCount(h.v) }} mẫu</span></button>
      </div>
      <p class="small pr-unit">Đơn vị: triệu đồng / m². Mỗi ô: giá thấp nhất – giá cao nhất.</p>

      <div class="pr-scroll">
        <table class="pr-table">
          <thead>
            <tr><th scope="col">Hạng mục</th><th v-for="g in PACKAGES" :key="g.v" scope="col">{{ g.t }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in ITEMS" :key="item.v">
              <th scope="row">{{ item.t }}</th>
              <td v-for="g in PACKAGES" :key="g.v">
                <div v-if="cell(item.v, g.v)" class="pr-cell" :class="{ 'is-dirty': dirty(cell(item.v, g.v)) }">
                  <div class="pr-inputs">
                    <label class="sr-only" :for="'min-' + cell(item.v, g.v).id">{{ item.t }}, {{ g.t }}: thấp nhất</label>
                    <input :id="'min-' + cell(item.v, g.v).id" v-model="edit[cell(item.v, g.v).id].min" type="number"
                           inputmode="decimal" min="0" step="0.01">
                    <span aria-hidden="true">–</span>
                    <label class="sr-only" :for="'max-' + cell(item.v, g.v).id">{{ item.t }}, {{ g.t }}: cao nhất</label>
                    <input :id="'max-' + cell(item.v, g.v).id" v-model="edit[cell(item.v, g.v).id].max" type="number"
                           inputmode="decimal" min="0" step="0.01">
                  </div>
                  <div class="pr-foot">
                    <span v-if="cell(item.v, g.v).nguon === 'mau'" class="chip chip-static pr-chip">Mẫu</span>
                    <span v-else class="small pr-who" :title="cell(item.v, g.v).cap_nhat_boi || ''">D3</span>
                    <button class="btn btn-secondary pr-save" type="button" :disabled="!dirty(cell(item.v, g.v)) || saving === cell(item.v, g.v).id"
                            @click="save(cell(item.v, g.v))">{{ saving === cell(item.v, g.v).id ? 'Đang lưu…' : 'Lưu' }}</button>
                  </div>
                  <p v-if="cellErr[cell(item.v, g.v).id]" class="field-err" role="alert">{{ cellErr[cell(item.v, g.v).id] }}</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </main>
</template>

<script setup>
/* Bảng đơn giá D8 (act-6: bộ phận dự toán cập nhật đơn giá, không sửa mã nguồn). KTS trưởng và admin. */
import { onMounted, reactive, ref } from 'vue'
import { getPrices, savePrice } from '@/api'

const HOUSES = [{ v: 'can_ho', t: 'Căn hộ / Chung cư' }, { v: 'nha_pho', t: 'Nhà phố' }, { v: 'biet_thu', t: 'Biệt thự' },
                { v: 'van_phong', t: 'Văn phòng' }, { v: 'thuong_mai', t: 'Thương mại / Showroom' }]
const ITEMS = [{ v: 'thiet_ke', t: 'Thiết kế' }, { v: 'phan_tho', t: 'Phần thô & cải tạo' },
               { v: 'hoan_thien', t: 'Hoàn thiện' }, { v: 'noi_that', t: 'Nội thất' }]
const PACKAGES = [{ v: 'co_ban', t: 'Cơ bản' }, { v: 'tieu_chuan', t: 'Tiêu chuẩn' }, { v: 'cao_cap', t: 'Cao cấp' }]

const rows = ref([])
const edit = reactive({})      // id -> { min, max } in million VND, as typed
const cellErr = reactive({})
const house = ref('can_ho')
const loading = ref(true)
const error = ref('')
const saving = ref(null)

const toM = v => Math.round(v / 10_000) / 100 // VND -> million, 2 decimals
const cell = (item, goi) => rows.value.find(r => r.loai_nha === house.value && r.hang_muc === item && r.goi === goi)
const sampleCount = h => rows.value.filter(r => r.loai_nha === h && r.nguon === 'mau').length
const dirty = r => String(edit[r.id].min) !== String(toM(r.gia_min)) || String(edit[r.id].max) !== String(toM(r.gia_max))

async function save(r) {
  delete cellErr[r.id]
  const lo = Number(edit[r.id].min), hi = Number(edit[r.id].max)
  if (edit[r.id].min === '' || edit[r.id].max === '' || !(lo >= 0) || !(hi >= 0)) { cellErr[r.id] = 'Nhập giá từ 0 trở lên'; return }
  if (lo > hi) { cellErr[r.id] = 'Giá thấp nhất phải nhỏ hơn hoặc bằng giá cao nhất'; return }
  saving.value = r.id
  try {
    const got = await savePrice(r.id, { gia_min: Math.round(lo * 1e6), gia_max: Math.round(hi * 1e6) })
    Object.assign(r, got)
    edit[r.id] = { min: toM(r.gia_min), max: toM(r.gia_max) }
  } catch (e) {
    cellErr[r.id] = e.status === 422 ? 'Giá thấp nhất phải nhỏ hơn hoặc bằng giá cao nhất' : 'Chưa lưu được: ' + e.message
  } finally { saving.value = null }
}

onMounted(async () => {
  try {
    rows.value = await getPrices()
    for (const r of rows.value) edit[r.id] = { min: toM(r.gia_min), max: toM(r.gia_max) }
  } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>

<style scoped>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.pr-tabs { margin-top: 24px; flex-wrap: wrap }
.pr-count { color: var(--faint) }
.pr-unit { margin: 14px 0 0; color: var(--dim) }
.pr-scroll { position: relative; margin-top: 14px; overflow-x: auto; max-width: 100% } /* keeps the absolute sr-only labels inside the scroll box */
.pr-table { border-collapse: collapse; min-width: 640px; width: 100% }
.pr-table th, .pr-table td { border-bottom: 1px solid var(--line-soft); padding: 12px 10px; text-align: left; vertical-align: top }
.pr-table thead th { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--faint); font-weight: 500 }
.pr-table tbody th { font-weight: 500; color: var(--ink); white-space: nowrap }
.pr-cell { display: grid; gap: 8px }
.pr-inputs { display: flex; align-items: center; gap: 6px }
.pr-inputs input { width: 5.5em; min-width: 0; background: var(--panel); color: var(--ink); border: 1px solid var(--line);
                   border-radius: var(--radius-sm); padding: 8px; font: inherit; font-size: 14px }
.pr-inputs input:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring); outline: none }
.pr-cell.is-dirty .pr-inputs input { border-color: var(--ink-2) }
.pr-foot { display: flex; align-items: center; gap: 8px }
.pr-chip { font-size: 11px; padding: 2px 8px }
.pr-who { color: var(--dim) }
.pr-save { padding: 4px 12px; min-height: 0; font-size: 13px }
</style>
