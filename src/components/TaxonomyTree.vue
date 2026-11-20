<template>
  <section class="tt">
    <h2 class="sr-only">Danh mục phân loại</h2>
    <p class="lead" style="margin-top:0">
      Các chiều và giá trị dùng cho bộ lọc, gắn nhãn và trợ lý. Đổi tên không đổi mã, nên link bộ lọc cũ vẫn dùng được.
    </p>
    <p v-if="error" class="field-err" role="alert">{{ error }}</p>
    <p v-if="loading && !dims.length" class="small">Đang tải…</p>
    <p v-if="note" class="tt-note" role="status">{{ note }}</p>

    <article v-for="(d, di) in dims" :key="d.id" class="tt-dim" :aria-labelledby="'dim-' + d.id">
      <header class="tt-dim-head">
        <div class="tt-dim-title">
          <template v-if="editDim === d.id">
            <label class="sr-only" :for="'dim-ten-' + d.id">Tên chiều</label>
            <input :id="'dim-ten-' + d.id" v-model="dimName" class="txt" maxlength="80" @keydown.enter.prevent="saveDimName(d)"
                   @keydown.esc="editDim = null">
            <button class="btn btn-primary btn-sm" type="button" :disabled="!!busy" @click="saveDimName(d)">Lưu</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="editDim = null">Huỷ</button>
          </template>
          <template v-else>
            <h3 :id="'dim-' + d.id" class="tt-dim-name">{{ d.ten }}</h3>
            <code class="tt-code">{{ d.ma_dinh_danh }}</code>
            <span v-if="d.cho_phep_nhieu_gia_tri" class="tt-tag">nhiều giá trị</span>
          </template>
        </div>
        <div class="tt-dim-tools">
          <label class="tt-switch">
            <input type="checkbox" :checked="d.hien_thi_cho_khach" :disabled="!!busy"
                   @change="setVisible(d, $event.target.checked)">
            Hiện cho khách
          </label>
          <button class="tt-icon" type="button" :disabled="di === 0 || !!busy" :aria-label="'Đưa «' + d.ten + '» lên'"
                  @click="move(d, 'up')"><Icon name="arrow-up" size="15" /></button>
          <button class="tt-icon" type="button" :disabled="di === dims.length - 1 || !!busy" :aria-label="'Đưa «' + d.ten + '» xuống'"
                  @click="move(d, 'down')"><Icon name="arrow-down" size="15" /></button>
          <button v-if="editDim !== d.id" class="tt-link" type="button" @click="startDimName(d)">Đổi tên</button>
        </div>
      </header>
      <p v-if="!d.hien_thi_cho_khach" class="tt-hint">Đang ẩn: khách không thấy chiều này trong bộ lọc; nhãn vẫn được giữ.</p>
      <p v-if="dimErr[d.id]" class="field-err" role="alert">{{ dimErr[d.id] }}</p>

      <ul class="tt-values">
        <li v-for="v in d.gia_tri" :key="v.id" class="tt-value">
          <template v-if="editVal === v.id">
            <form class="tt-form" @submit.prevent="saveValue(v)">
              <div class="field"><label :for="'v-ten-' + v.id">Tên</label>
                <input :id="'v-ten-' + v.id" v-model="form.ten" class="txt" maxlength="120" required></div>
              <div class="field"><label :for="'v-mota-' + v.id">Mô tả</label>
                <input :id="'v-mota-' + v.id" v-model="form.mo_ta" class="txt" maxlength="500"></div>
              <div class="field"><label :for="'v-syn-' + v.id">Từ đồng nghĩa (cách nhau bằng dấu phẩy)</label>
                <input :id="'v-syn-' + v.id" v-model="form.syn" class="txt" :aria-describedby="'v-syn-h-' + v.id">
                <span :id="'v-syn-h-' + v.id" class="tt-hint">Từ khách hay dùng, vd «bắc âu». Trợ lý hiểu cả khi khách gõ không dấu.</span></div>
              <p v-if="formErr" class="field-err" role="alert">{{ formErr }}</p>
              <div class="row g10">
                <button class="btn btn-primary btn-sm" :disabled="!!busy">Lưu</button>
                <button class="btn btn-ghost btn-sm" type="button" @click="editVal = null">Huỷ</button>
              </div>
            </form>
          </template>
          <template v-else>
            <div class="tt-value-main">
              <span class="tt-value-name">{{ v.ten }}</span>
              <code class="tt-code">{{ v.ma_dinh_danh }}</code>
            </div>
            <p v-if="v.tu_dong_nghia?.length" class="tt-syn">{{ v.tu_dong_nghia.join(', ') }}</p>
            <p class="tt-usage num">{{ v.so_khong_gian }} không gian · {{ v.so_da_dang }} đã đăng · {{ v.so_du_an }} dự án</p>
            <div class="tt-value-tools">
              <button class="tt-link" type="button" @click="startValue(v)">Sửa</button>
              <button v-if="d.co_the_gop && d.gia_tri.length > 1" class="tt-link" type="button" @click="openMerge(d, v)">Gộp vào…</button>
            </div>
          </template>
        </li>
        <li v-if="!d.gia_tri.length" class="tt-hint">Chưa có giá trị.</li>
      </ul>

      <form v-if="addTo === d.id" class="tt-form tt-add" @submit.prevent="createValue(d)">
        <div class="field"><label :for="'n-ten-' + d.id">Tên giá trị mới</label>
          <input :id="'n-ten-' + d.id" v-model="form.ten" class="txt" maxlength="120" required
                 :aria-describedby="'n-ma-' + d.id">
          <span :id="'n-ma-' + d.id" class="tt-hint">Mã: <code>{{ slug(form.ten) || '—' }}</code> (không đổi về sau)</span></div>
        <div class="field"><label :for="'n-mota-' + d.id">Mô tả</label>
          <input :id="'n-mota-' + d.id" v-model="form.mo_ta" class="txt" maxlength="500"></div>
        <div class="field"><label :for="'n-syn-' + d.id">Từ đồng nghĩa (cách nhau bằng dấu phẩy)</label>
          <input :id="'n-syn-' + d.id" v-model="form.syn" class="txt"></div>
        <p v-if="formErr" class="field-err" role="alert">{{ formErr }}</p>
        <div class="row g10">
          <button class="btn btn-primary btn-sm" :disabled="!!busy">Thêm</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="addTo = null">Huỷ</button>
        </div>
      </form>
      <button v-else class="tt-link tt-add-btn" type="button" @click="startAdd(d)">+ Thêm giá trị</button>
    </article>

    <!-- a new dimension -->
    <form v-if="newDim" class="tt-dim tt-form" @submit.prevent="createDimension">
      <h3 class="tt-dim-name">Chiều mới</h3>
      <div class="field"><label for="nd-ten">Tên chiều</label>
        <input id="nd-ten" v-model="dimForm.ten" class="txt" maxlength="80" required aria-describedby="nd-ma">
        <span id="nd-ma" class="tt-hint">Mã: <code>{{ slug(dimForm.ten) || '—' }}</code> (không đổi về sau)</span></div>
      <label class="tt-switch"><input v-model="dimForm.nhieu" type="checkbox"> Một không gian có thể mang nhiều giá trị</label>
      <label class="tt-switch"><input v-model="dimForm.hien_thi" type="checkbox"> Hiện cho khách trong bộ lọc</label>
      <p v-if="formErr" class="field-err" role="alert">{{ formErr }}</p>
      <div class="row g10">
        <button class="btn btn-primary btn-sm" :disabled="!!busy">Tạo chiều</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="newDim = false">Huỷ</button>
      </div>
    </form>
    <button v-else-if="dims.length" class="btn btn-secondary" type="button" @click="startNewDim">+ Thêm chiều</button>

    <!-- recent changes -->
    <section v-if="log.length" class="tt-log" aria-labelledby="tt-log-h">
      <h3 id="tt-log-h" class="tt-dim-name">Gần đây</h3>
      <ol>
        <li v-for="l in log" :key="l.id">
          <span class="num tt-when">{{ when(l.created_at) }}</span>
          <span>{{ describe(l) }}</span>
          <span class="tt-who">{{ l.email || 'hệ thống' }}</span>
        </li>
      </ol>
    </section>

    <!-- merge: names what moves, nothing happens before "Gộp" -->
    <dialog ref="mergeEl" class="tt-dialog" aria-labelledby="mg-h" @close="merging = null">
      <form v-if="merging" method="dialog" class="tt-form" @submit.prevent="doMerge">
        <h3 id="mg-h" class="tt-dim-name">Gộp «{{ merging.v.ten }}»</h3>
        <div class="field"><label for="mg-dst">Gộp vào</label>
          <select id="mg-dst" v-model="mergeTo" class="txt" required>
            <option v-for="o in merging.d.gia_tri.filter(x => x.id !== merging.v.id)" :key="o.id" :value="o.id">{{ o.ten }}</option>
          </select></div>
        <p class="tt-warn" role="note">
          «{{ merging.v.ten }}» đang gắn cho <strong class="num">{{ merging.v.so_khong_gian }}</strong> không gian
          (<span class="num">{{ merging.v.so_da_dang }}</span> đã đăng) thuộc <strong class="num">{{ merging.v.so_du_an }}</strong> dự án.
          Sau khi gộp, các nhãn này chuyển sang «{{ targetName }}» và «{{ merging.v.ten }}» bị xoá. Không hoàn tác được.
        </p>
        <p v-if="formErr" class="field-err" role="alert">{{ formErr }}</p>
        <div class="row g10">
          <button class="btn btn-primary btn-sm" :disabled="!!busy || !mergeTo">Gộp</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="mergeEl.close()">Huỷ</button>
        </div>
      </form>
    </dialog>
  </section>
</template>

<script setup>
import Icon from '@/components/Icon.vue'
/* Tab "Danh mục" of /quan-tri/phan-loai (seq-15): dimensions and values with usage, edits, merge, change log.
 * After each save the tree is reloaded from the server, so counts and log are always the server's. */
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { addDimension, addValue, editDimension, editValue, getTaxonomyAdmin, mergeValue } from '@/api'
import { slug } from '@/lib/slug'

const dims = ref([])
const log = ref([])
const loading = ref(true)
const error = ref('')
const note = ref('')
const busy = ref('')
const dimErr = reactive({})

const editDim = ref(null)
const dimName = ref('')
const editVal = ref(null)
const addTo = ref(null)
const newDim = ref(false)
const form = reactive({ ten: '', mo_ta: '', syn: '' })
const dimForm = reactive({ ten: '', nhieu: false, hien_thi: true })
const formErr = ref('')

const mergeEl = ref(null)
const merging = ref(null) // { d, v }
const mergeTo = ref(null)

const synList = s => s.split(',').map(x => x.trim()).filter(Boolean)
const targetName = computed(() => merging.value?.d.gia_tri.find(x => x.id === mergeTo.value)?.ten || '…')

async function load() {
  loading.value = true
  try {
    const r = await getTaxonomyAdmin()
    dims.value = r.chieu
    log.value = r.gan_day
    error.value = ''
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

const message = e => (e.status === 409 ? 'Đã có trong chiều này (trùng mã).' : typeof e.detail === 'string' ? e.detail
  : Array.isArray(e.detail) ? e.detail.map(x => x.msg).join('; ') : e.message)

async function run(key, call, done) {
  busy.value = key; formErr.value = ''; note.value = ''
  try {
    const out = await call()
    await load()
    done?.(out)
    return true
  } catch (e) { formErr.value = message(e); return false }
  finally { busy.value = '' }
}

// ── dimensions ──
function startDimName(d) { editDim.value = d.id; dimName.value = d.ten }
async function saveDimName(d) {
  if (!dimName.value.trim()) return
  delete dimErr[d.id]
  const ok = await run('dim', () => editDimension(d.id, { ten: dimName.value.trim() }), () => { editDim.value = null })
  if (!ok) dimErr[d.id] = formErr.value
}
async function setVisible(d, on) {
  delete dimErr[d.id]
  const ok = await run('dim', () => editDimension(d.id, { hien_thi_cho_khach: on }),
    () => { note.value = `«${d.ten}» ${on ? 'đã hiện' : 'đã ẩn'} trong bộ lọc của khách.` })
  if (!ok) { dimErr[d.id] = formErr.value; await load() }
}
async function move(d, dir) {
  delete dimErr[d.id]
  const ok = await run('dim', () => editDimension(d.id, { move: dir }))
  if (!ok) { dimErr[d.id] = formErr.value; return }
  // after run(): the buttons are enabled again only once busy is cleared (a disabled button cannot take focus);
  // at the top or bottom the pressed button is disabled, so focus falls back to the other arrow
  await nextTick()
  const label = `Đưa «${d.ten}» `
  const btn = document.querySelector(`[aria-label="${label}${dir === 'up' ? 'lên' : 'xuống'}"]`)
  ;(btn && !btn.disabled ? btn : document.querySelector(`[aria-label="${label}${dir === 'up' ? 'xuống' : 'lên'}"]`))?.focus()
}
function startNewDim() { Object.assign(dimForm, { ten: '', nhieu: false, hien_thi: true }); formErr.value = ''; newDim.value = true; focus('nd-ten') }
async function createDimension() {
  await run('new-dim', () => addDimension({ ten: dimForm.ten.trim(), cho_phep_nhieu_gia_tri: dimForm.nhieu, hien_thi_cho_khach: dimForm.hien_thi }),
    () => { note.value = `Đã tạo chiều «${dimForm.ten.trim()}».`; newDim.value = false })
}

// ── values ──
function resetForm(v) { Object.assign(form, { ten: v?.ten || '', mo_ta: v?.mo_ta || '', syn: (v?.tu_dong_nghia || []).join(', ') }); formErr.value = '' }
function startValue(v) { addTo.value = null; resetForm(v); editVal.value = v.id; focus('v-ten-' + v.id) }
function startAdd(d) { editVal.value = null; resetForm(); addTo.value = d.id; focus('n-ten-' + d.id) }
async function saveValue(v) {
  await run('val', () => editValue(v.id, { ten: form.ten.trim(), mo_ta: form.mo_ta, tu_dong_nghia: synList(form.syn) }),
    () => { editVal.value = null; note.value = `Đã lưu «${form.ten.trim()}».` })
}
async function createValue(d) {
  await run('add', () => addValue(d.id, { ten: form.ten.trim(), mo_ta: form.mo_ta || null, tu_dong_nghia: synList(form.syn) }),
    () => { note.value = `Đã thêm «${form.ten.trim()}» vào «${d.ten}».`; addTo.value = null })
}

// ── merge ──
function openMerge(d, v) {
  formErr.value = ''
  merging.value = { d, v }
  mergeTo.value = d.gia_tri.find(x => x.id !== v.id)?.id ?? null
  nextTick(() => mergeEl.value?.showModal())
}
async function doMerge() {
  const { v } = merging.value
  const into = targetName.value
  await run('merge', () => mergeValue(v.id, mergeTo.value), out => {
    mergeEl.value.close()
    const n = out?.so_anh_cap_nhat || 0 // seq-15 b20 (admin-tools): the search index catches up in the background
    note.value = `Đã gộp «${v.ten}» vào «${into}»` + (n ? `; chỉ mục đang được cập nhật cho ${n} ảnh.` : '.')
  })
}

function focus(id) { nextTick(() => document.getElementById(id)?.focus()) }

// ── log ──
const ACTION = { them_chieu: 'Thêm chiều', sua_chieu: 'Sửa chiều', them_gia_tri: 'Thêm giá trị', sua_gia_tri: 'Sửa giá trị', gop_gia_tri: 'Gộp giá trị' }
const FIELD = { ten: 'tên', mo_ta: 'mô tả', tu_dong_nghia: 'từ đồng nghĩa', hien_thi: 'hiện cho khách', thu_tu: 'thứ tự' }
function describe(l) {
  const head = `${ACTION[l.hanh_dong] || l.hanh_dong} ${l.doi_tuong}`
  if (l.hanh_dong === 'gop_gia_tri') return `${head} → ${l.sau?.dich} (${l.sau?.so_khong_gian ?? 0} không gian)`
  if (l.hanh_dong.startsWith('sua') && l.sau) {
    return head + ': ' + Object.keys(l.sau).map(k => `${FIELD[k] || k} ${fmt(l.truoc?.[k])} → ${fmt(l.sau[k])}`).join('; ')
  }
  return head
}
const fmt = x => (Array.isArray(x) ? (x.join(', ') || '∅') : x === true ? 'có' : x === false ? 'không' : x ?? '∅')
const when = t => new Date(t).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })

onMounted(load)
</script>

<style scoped>
.txt { width: 100% }  /* skin: global .txt (app.css) */
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.tt-note { margin: 0 0 12px; font-size: 14px; color: var(--ink) }
.tt-hint { margin: 0; font-size: 13px; color: var(--dim) }

.tt-dim { border: 1px solid var(--line); border-radius: var(--radius-md); padding: clamp(14px, 2.5vw, 20px); margin: 0 0 16px }
.tt-dim-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px 16px }
.tt-dim-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 10px; min-width: 0 }
.tt-dim-title .txt { width: auto; flex: 1 1 200px }
.tt-dim-name { margin: 0; font-size: 18px; font-weight: 600; color: var(--ink) }
.tt-code { font-family: var(--font-mono); font-size: 12px; color: var(--dim); overflow-wrap: anywhere }
.tt-tag { font-size: 12px; color: var(--dim); border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px }
.tt-dim-tools { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px }
.tt-switch { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; color: var(--ink); cursor: pointer }
.tt-switch input { accent-color: var(--accent) }
.tt-icon { display: inline-grid; place-items: center; width: 34px; height: 34px; border: 1px solid var(--line); border-radius: var(--radius-pill); background: none; color: var(--ink);
           font-size: 15px; cursor: pointer }
.tt-icon:disabled { opacity: .35; cursor: default }
.tt-link { background: none; border: 0; padding: 4px 0; font: inherit; font-size: 14px; color: var(--ink);
           text-decoration: underline; text-underline-offset: 3px; cursor: pointer }
.tt-icon:focus-visible, .tt-link:focus-visible { outline: none; box-shadow: var(--focus-ring) }

.tt-values { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 0 }
.tt-value { display: grid; grid-template-columns: 1fr; gap: 2px 16px; padding: 10px 0; border-top: 1px solid var(--line-soft) }
@media (min-width: 760px) {
  .tt-value { grid-template-columns: minmax(180px, 1.2fr) 2fr auto auto; align-items: baseline }
  .tt-value > .tt-form { grid-column: 1 / -1 }
}
.tt-value-main { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px }
.tt-value-name { color: var(--ink); font-weight: 500 }
.tt-syn { margin: 0; font-size: 13px; color: var(--dim); overflow-wrap: anywhere }
.tt-usage { margin: 0; font-size: 13px; color: var(--dim); white-space: nowrap }
.tt-value-tools { display: flex; gap: 14px }
.tt-add-btn { margin-top: 10px }

.tt-form { display: grid; gap: 12px; max-width: 560px }
.tt-add { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line-soft) }
.tt-form .field { display: grid; gap: 4px }
.tt-form label { font-size: 14px; color: var(--ink) }

.tt-log { margin-top: 32px }
.tt-log ol { list-style: none; margin: 10px 0 0; padding: 0; display: grid; gap: 6px }
.tt-log li { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 13px; color: var(--ink); overflow-wrap: anywhere }
.tt-when, .tt-who { color: var(--dim) }

.tt-dialog { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--page); color: var(--ink);
             padding: 20px; width: min(480px, calc(100vw - 32px)) }
.tt-dialog::backdrop { background: rgba(0, 0, 0, 0.55) }
.tt-warn { margin: 0; font-size: 14px; line-height: 1.6; color: var(--ink) }
</style>
