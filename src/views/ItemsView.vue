<template>
  <main class="wrap wrap-wide page-top it-page">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Thư viện món đồ</h1>
    <p class="lead" style="margin-top:10px">
      Món đồ và vật liệu dùng để gắn điểm nóng trên ảnh. Khách chỉ thấy tên điểm; nhà cung cấp và ghi chú chỉ nội bộ.
    </p>

    <div class="it-bar">
      <label class="sr-only" for="it-q">Tìm món đồ</label>
      <input id="it-q" v-model="q" class="txt it-search" type="search" placeholder="Tìm theo tên, loại, vật liệu">
      <span class="small num">{{ shown.length }} món đồ</span>
    </div>
    <p v-if="note" class="small" role="status" style="margin-top:12px">{{ note }}</p>
    <p v-if="error" class="small" style="margin-top:12px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!rows" class="small" style="margin-top:20px">Đang tải…</p>
    <p v-else-if="!rows.length" class="small" style="margin-top:20px">
      Chưa có món đồ nào. Tạo món đồ khi gắn điểm nóng ở trang Duyệt.
    </p>

    <div v-else class="it-list" role="table" aria-label="Món đồ">
      <div class="it-head" role="row">
        <span role="columnheader">Tên</span><span role="columnheader">Loại</span><span role="columnheader">Vật liệu</span>
        <span role="columnheader">Màu</span><span role="columnheader">Nhà cung cấp</span><span role="columnheader">Khoảng giá</span><span role="columnheader">Dịch vụ</span><span role="columnheader">Số ảnh</span>
        <span role="columnheader"><span class="sr-only">Thao tác</span></span>
      </div>
      <div v-for="it in shown" :key="it.id" class="it-row" role="row">
        <span role="cell" class="it-name">{{ it.ten }}</span>
        <span role="cell"><span class="it-k">Loại</span>{{ it.phan_loai || '–' }}</span>
        <span role="cell"><span class="it-k">Vật liệu</span>{{ it.vat_lieu || '–' }}</span>
        <span role="cell"><span class="it-k">Màu</span>{{ it.mau_sac || '–' }}</span>
        <span role="cell"><span class="it-k">Nhà cung cấp</span>{{ it.nha_cung_cap || '–' }}</span>
        <span role="cell"><span class="it-k">Khoảng giá</span>{{ it.khoang_gia || '–' }}</span>
        <span role="cell"><span class="it-k">Dịch vụ</span>{{ it.dich_vu || '–' }}</span>
        <span role="cell" class="num"><span class="it-k">Số ảnh</span>{{ it.so_anh }}</span>
        <span role="cell" class="it-act">
          <button type="button" class="btn btn-ghost" :aria-label="'Sửa ' + it.ten" @click="edit(it, $event)">Sửa</button>
          <button type="button" class="btn btn-ghost" :aria-label="'Xoá ' + it.ten" @click="remove(it)">Xoá</button>
        </span>
        <div v-if="inUse.id === it.id" class="it-inuse" role="alert">
          <p class="small" style="margin:0">Đang dùng ở {{ inUse.n }} ảnh, chưa xoá được. Gỡ món đồ khỏi các điểm nóng trước:</p>
          <ul class="it-photos">
            <li v-for="s in inUse.spaces" :key="s.id">
              <router-link :to="'/khong-gian/' + s.id">#{{ s.id }} {{ s.relative_path }}</router-link>
              <span v-if="s.review_status" class="small"> · {{ STATUS_VI[s.review_status] || s.review_status }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <dialog ref="dlg" class="it-dialog" aria-labelledby="it-dlg-h" @close="onClose">
      <form method="dialog" class="stack" style="gap:12px" @submit.prevent="saveEdit">
        <h2 id="it-dlg-h" class="h-4" style="margin:0">Sửa món đồ</h2>
        <label v-for="f in FIELDS" :key="f.k" class="it-field">{{ f.t }}
          <input v-if="f.k !== 'ghi_chu'" v-model="form[f.k]" class="txt" :maxlength="f.max" :required="f.k === 'ten'">
          <textarea v-else v-model="form.ghi_chu" class="txt" rows="3" maxlength="500"></textarea>
        </label>
        <ServicePicker v-model="form.dich_vu_id" :services="services" id="it-dv" />
        <p v-if="formError" class="field-err" role="alert">{{ formError }}</p>
        <div class="row g10">
          <button class="btn btn-primary" type="submit" :disabled="busy">Lưu</button>
          <button class="btn btn-ghost" type="button" @click="dlg.close()">Huỷ</button>
        </div>
      </form>
    </dialog>
  </main>
</template>

<script setup>
/* Thư viện món đồ (change hotspot-items; class-1 MonDo) cho KTS, KTS trưởng, admin. */
import { computed, reactive, ref } from 'vue'
import { STATUS_VI, deleteItem, itemServices, itemSpaces, searchItems, updateItem } from '@/api'
import ServicePicker from '@/components/ServicePicker.vue'

const FIELDS = [
  { k: 'ten', t: 'Tên', max: 120 }, { k: 'phan_loai', t: 'Loại', max: 60 }, { k: 'kieu_dang', t: 'Kiểu dáng', max: 60 },
  { k: 'vat_lieu', t: 'Vật liệu', max: 60 }, { k: 'mau_sac', t: 'Màu', max: 40 },
  { k: 'nha_cung_cap', t: 'Nhà cung cấp (nội bộ)', max: 120 }, { k: 'khoang_gia', t: 'Khoảng giá (nội bộ)', max: 60 },
  { k: 'ghi_chu', t: 'Ghi chú (nội bộ)', max: 500 }
]
const rows = ref(null)
const q = ref('')
const error = ref('')
const note = ref('')
const busy = ref(false)
const dlg = ref(null)
const form = reactive({})
const formError = ref('')
const inUse = reactive({ id: null, n: 0, spaces: [] })
const services = ref([])
itemServices().then(r => { services.value = r }).catch(() => {})
let editing = null
let opener = null

const fold = t => ((t || '').toLowerCase().replace(/đ/g, 'd').normalize('NFD').replace(/[̀-ͯ]/g, '').match(/[a-z0-9]+/g) || []).join(' ')
const shown = computed(() => {
  const needle = fold(q.value)
  return (rows.value || []).filter(it => !needle || fold([it.ten, it.phan_loai, it.vat_lieu].join(' ')).includes(needle))
})

async function load() {
  try { rows.value = await searchItems('', 500); error.value = '' } catch (e) { error.value = e.message }
}
function edit(it, e) {
  editing = it; opener = e.currentTarget; formError.value = ''
  for (const f of FIELDS) form[f.k] = it[f.k] || ''
  form.dich_vu_id = it.dich_vu_id ?? null
  dlg.value.showModal()
}
function onClose() { opener?.focus() }
async function saveEdit() {
  busy.value = true; formError.value = ''
  try {
    const body = { ...Object.fromEntries(FIELDS.map(f => [f.k, form[f.k].trim() || null])), dich_vu_id: form.dich_vu_id }
    await updateItem(editing.id, body)
    dlg.value.close(); await load()
    note.value = `Đã lưu «${body.ten}».` // after the list shows it
  } catch (e) {
    formError.value = e.status === 409 ? `Đã có món đồ «${e.detail?.existing?.ten}».` : e.message
  } finally { busy.value = false }
}
async function remove(it) {
  Object.assign(inUse, { id: null, n: 0, spaces: [] }); note.value = ''
  if (!window.confirm(`Xoá món đồ «${it.ten}»?`)) return
  try {
    await deleteItem(it.id)
    await load(); note.value = `Đã xoá «${it.ten}».`
  } catch (e) {
    if (e.status !== 409) { error.value = e.message; return }
    const r = await itemSpaces(it.id).catch(() => ({ spaces: [] }))
    Object.assign(inUse, { id: it.id, n: e.detail?.so_anh ?? r.spaces.length, spaces: r.spaces })
  }
}
load()
</script>

<style scoped>
.it-page { padding-bottom: clamp(28px, 4vw, 56px) }
.it-bar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-top: 20px }
.txt { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 8px 10px; min-height: 40px; color-scheme: dark; font: inherit }
.txt:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring); outline: none }
.it-search { flex: 1 1 260px; max-width: 420px; min-width: 0 }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.it-list { margin-top: 16px; display: grid; gap: 8px }
.it-head { display: none }
.it-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 14px; padding: 12px 14px; border: 1px solid var(--line);
  border-radius: var(--radius-md); background: var(--panel); font-size: 14px; color: var(--ink-2); min-width: 0 }
.it-row > span { min-width: 0; overflow-wrap: anywhere }
.it-name { grid-column: 1 / -1; color: var(--ink); font-size: 15px }
.it-k { display: block; font-size: 11px; color: var(--faint) }
.it-act { grid-column: 1 / -1; display: flex; gap: 6px }
.it-inuse { grid-column: 1 / -1; display: grid; gap: 6px; padding: 10px; border: 1px solid var(--danger); border-radius: var(--radius-sm) }
.it-photos { margin: 0; padding-left: 18px; font-size: 13px }
@media (min-width: 760px) {
  .it-head, .it-row { grid-template-columns: minmax(0, 2fr) 1fr 1fr .8fr 1.2fr 1fr 1.4fr .6fr auto; align-items: center }
  .it-head { display: grid; gap: 14px; padding: 0 14px; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--faint) }
  .it-name, .it-act { grid-column: auto }
  .it-k { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0) }
}
.it-dialog { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--page); color: var(--ink);
  padding: 20px; width: min(520px, calc(100vw - 32px)) }
.it-dialog::backdrop { background: rgba(0, 0, 0, 0.55) }
.it-field { display: grid; gap: 4px; font-size: 13px; color: var(--dim) }
.it-field .txt { width: 100%; background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 8px 10px; font: inherit }
</style>
