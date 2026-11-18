<template>
  <div class="he">
    <p class="small he-help" :id="uid + '-help'">
      Bấm vào ảnh để thêm điểm, kéo điểm để dời. Chọn một điểm rồi dùng phím mũi tên để dời (Shift: bước lớn), Delete để xoá.
    </p>
    <div ref="stage" class="he-stage" @pointerdown="onStagePointer">
      <img :src="src" alt="" draggable="false">
      <button v-for="(p, i) in points" :key="p.key" :ref="el => (dotEls[i] = el)" type="button" class="he-dot"
              :class="{ 'is-sel': sel === i, 'is-hand': p.nguon_tao === 'thu_cong' }"
              :style="{ left: p.x * 100 + '%', top: p.y * 100 + '%' }"
              :aria-label="'Điểm ' + (i + 1) + ': ' + (p.label_vi || 'chưa đặt tên')" :aria-pressed="String(sel === i)"
              :aria-describedby="uid + '-help'"
              @pointerdown.stop="startDrag($event, i)" @click.stop="sel = i" @keydown="onDotKey($event, i)">{{ i + 1 }}</button>
    </div>

    <div class="row g10 he-tools">
      <button type="button" class="btn btn-secondary" @click="addCentre">Thêm điểm</button>
      <span class="small">{{ points.length }}/{{ MAX }} điểm</span>
    </div>

    <p v-if="!points.length" class="small">Chưa có điểm nào.</p>
    <ol class="he-rows">
      <li v-for="(p, i) in points" :key="p.key" class="he-row" :class="{ 'is-sel': sel === i }" @focusin="sel = i">
        <span class="num he-n">{{ i + 1 }}</span>
        <span class="he-chip" :class="{ 'is-hand': p.nguon_tao === 'thu_cong' }">{{ p.nguon_tao === 'thu_cong' ? 'Thủ công' : 'AI' }}</span>
        <input v-model="p.label_vi" class="txt he-name" maxlength="120" :aria-label="'Tên điểm ' + (i + 1) + ' (khách thấy)'"
               :aria-invalid="String(!!errors[i])" :aria-describedby="errors[i] ? uid + '-e' + i : null">

        <div class="he-pick">
          <div v-if="p.mon_do_id && byId[p.mon_do_id]" class="he-linked">
            <span>{{ byId[p.mon_do_id].ten }}</span>
            <button type="button" class="btn btn-ghost he-x" :aria-label="'Bỏ liên kết món đồ của điểm ' + (i + 1)"
                    @click="p.mon_do_id = null"><Icon name="close" /></button>
          </div>
          <template v-else>
            <input class="txt" role="combobox" :aria-expanded="String(pick.row === i && pick.open)"
                   :aria-controls="uid + '-lb' + i" :aria-activedescendant="pick.row === i && pick.active >= 0 ? uid + '-o' + pick.active : null"
                   :aria-label="'Món đồ của điểm ' + (i + 1)" placeholder="Tìm hoặc tạo món đồ…" autocomplete="off"
                   :value="pick.row === i ? pick.q : ''" @input="onQuery(i, $event.target.value)" @focus="openPick(i)"
                   @keydown="onPickKey($event, i)" @blur="closeSoon">
            <ul v-if="pick.row === i && pick.open" :id="uid + '-lb' + i" class="he-lb" role="listbox">
              <li v-for="(o, k) in options" :id="uid + '-o' + k" :key="o.id ?? 'new'" role="option"
                  :aria-selected="String(pick.active === k)" :class="{ 'is-active': pick.active === k }"
                  @mousedown.prevent="choose(i, o)">
                <template v-if="o.id">{{ o.ten }} <span class="small">{{ [o.phan_loai, o.vat_lieu, o.mau_sac].filter(Boolean).join(' · ') }}</span></template>
                <template v-else>+ Tạo món đồ «{{ o.ten }}»</template>
              </li>
              <li v-if="!options.length" class="small he-empty" role="option" aria-disabled="true">Gõ tên để tìm hoặc tạo</li>
            </ul>
          </template>
        </div>
        <button type="button" class="btn btn-ghost" :aria-label="'Xoá điểm ' + (i + 1)" @click="remove(i)">Xoá</button>
        <span v-if="errors[i]" :id="uid + '-e' + i" class="field-err he-err" role="alert">{{ errors[i] }}</span>

        <form v-if="creating.row === i" class="he-new" @submit.prevent="createAndLink(i)">
          <p class="small" style="margin:0">Món đồ mới: <strong>{{ creating.ten }}</strong></p>
          <div class="he-grid">
            <label>Loại<input v-model="creating.phan_loai" class="txt" maxlength="60" placeholder="vd: Sofa, Đèn thả"></label>
            <label>Kiểu dáng<input v-model="creating.kieu_dang" class="txt" maxlength="60"></label>
            <label>Vật liệu<input v-model="creating.vat_lieu" class="txt" maxlength="60" :list="uid + '-mat'"></label>
            <label>Màu<input v-model="creating.mau_sac" class="txt" maxlength="40"></label>
            <label class="he-wide">Nhà cung cấp (chỉ nội bộ)<input v-model="creating.nha_cung_cap" class="txt" maxlength="120"></label>
            <ServicePicker :id="uid + '-dv'" v-model="creating.dich_vu_id" class="he-wide" :services="services" />
          </div>
          <p v-if="creating.error" class="field-err" role="alert">{{ creating.error }}</p>
          <div class="row g10">
            <button class="btn btn-primary" type="submit" :disabled="creating.busy">Tạo và gắn</button>
            <button class="btn btn-ghost" type="button" @click="creating.row = -1">Huỷ</button>
          </div>
        </form>
      </li>
    </ol>
    <datalist :id="uid + '-mat'"><option v-for="m in materials" :key="m" :value="m" /></datalist>

    <p v-if="error" class="field-err" role="alert">{{ error }}</p>
    <div class="row g10">
      <button class="btn btn-primary" type="button" :disabled="busy" @click="save">{{ busy ? 'Đang lưu…' : 'Lưu điểm nóng' }}</button>
      <button class="btn btn-ghost" type="button" @click="$emit('close')">Đóng</button>
    </div>
  </div>
</template>

<script setup>
import Icon from '@/components/Icon.vue'
/* Gắn hotspot món đồ (seq-14; change hotspot-items) cho KTS: thêm, kéo, dời bằng phím, đặt tên, gắn món đồ trong thư viện.
   Khách chỉ thấy tên điểm; nhà cung cấp không bao giờ rời trang quản trị. */
import { computed, nextTick, reactive, ref, useId } from 'vue'
import { createItem, getTaxonomy, itemServices, saveHotspots, searchItems } from '@/api'
import ServicePicker from '@/components/ServicePicker.vue'

const props = defineProps({
  spaceId: { type: Number, required: true },
  src: { type: String, required: true },
  objects: { type: Array, default: () => [] }
})
const emit = defineEmits(['saved', 'close'])

const MAX = 30
const uid = 'he' + useId()
let seq = 0
const points = ref(props.objects.map((o, index) => ({
  key: seq++, index, x: o.hotspot_anchor[0], y: o.hotspot_anchor[1], label_vi: o.label_vi || o.label || '',
  auto: o.label_vi || o.label || '', mon_do_id: o.mon_do_id ?? null, nguon_tao: o.nguon_tao || 'ai'
})))
const sel = ref(-1)
const stage = ref(null)
const dotEls = []
const busy = ref(false)
const error = ref('')
const errors = reactive({})

/* library: all items once (tens, not thousands), searched locally while typing */
const library = ref([])
const byId = computed(() => Object.fromEntries(library.value.map(it => [it.id, it])))
searchItems('', 500).then(r => { library.value = r }).catch(() => {})
const materials = ref([])
getTaxonomy().then(d => { materials.value = (d.find(x => x.ma_dinh_danh === 'vat_lieu')?.values || []).map(v => v.ten) }).catch(() => {})

const clamp = v => Math.min(1, Math.max(0, Math.round(v * 10000) / 10000))
function posOf(e) {
  const r = stage.value.getBoundingClientRect()
  return { x: clamp((e.clientX - r.left) / r.width), y: clamp((e.clientY - r.top) / r.height) }
}
function add(x, y) {
  if (points.value.length >= MAX) { error.value = `Tối đa ${MAX} điểm.`; return -1 }
  points.value.push({ key: seq++, index: null, x, y, label_vi: '', auto: '', mon_do_id: null, nguon_tao: 'thu_cong' })
  sel.value = points.value.length - 1
  return sel.value
}
function onStagePointer(e) {
  const img = stage.value.querySelector('img') // a cached image may finish before any load listener runs
  if (e.button !== 0 || !img?.complete || !img.naturalWidth) return
  e.preventDefault() // the mousedown would otherwise take focus away from the new point's name field
  const { x, y } = posOf(e)
  if (add(x, y) >= 0) focusName(sel.value)
}
async function focusName(i) {
  await nextTick()
  stage.value?.parentElement.querySelectorAll('.he-name')[i]?.focus()
}
async function addCentre() {
  const i = add(0.5, 0.5)
  if (i < 0) return
  await nextTick(); dotEls[i]?.focus()
}
function startDrag(e, i) {
  sel.value = i
  const dot = e.currentTarget
  dot.setPointerCapture(e.pointerId)
  const move = ev => { const { x, y } = posOf(ev); points.value[i].x = x; points.value[i].y = y }
  const up = () => { dot.removeEventListener('pointermove', move); dot.removeEventListener('pointerup', up) }
  dot.addEventListener('pointermove', move)
  dot.addEventListener('pointerup', up)
}
function onDotKey(e, i) {
  const step = e.shiftKey ? 0.1 : 0.01
  const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key]
  if (d) {
    e.preventDefault(); sel.value = i
    points.value[i].x = clamp(points.value[i].x + d[0]); points.value[i].y = clamp(points.value[i].y + d[1])
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    e.preventDefault(); remove(i)
  }
}
async function remove(i) {
  points.value.splice(i, 1)
  delete errors[i]
  sel.value = Math.min(i, points.value.length - 1)
  await nextTick(); (dotEls[sel.value] || stage.value)?.focus?.()
}

/* item combobox */
const pick = reactive({ row: -1, q: '', open: false, active: -1 })
const options = computed(() => {
  const q = fold(pick.q)
  const hits = library.value.filter(it => !q || fold([it.ten, it.phan_loai, it.vat_lieu].filter(Boolean).join(' ')).includes(q)).slice(0, 8)
  const exact = hits.some(it => fold(it.ten) === q)
  return pick.q.trim() && !exact ? [...hits, { id: null, ten: pick.q.trim() }] : hits
})
function fold(t) {
  return ((t || '').toLowerCase().replace(/đ/g, 'd').normalize('NFD').replace(/[̀-ͯ]/g, '').match(/[a-z0-9]+/g) || []).join(' ')
}
function openPick(i) { if (pick.row !== i) pick.q = ''; Object.assign(pick, { row: i, open: true, active: -1 }) }
function onQuery(i, v) { Object.assign(pick, { row: i, q: v, open: true, active: -1 }) }
let closer = null
function closeSoon() { clearTimeout(closer); closer = setTimeout(() => { pick.open = false }, 150) }
function onPickKey(e, i) {
  const n = options.value.length
  if (e.key === 'ArrowDown') { e.preventDefault(); pick.open = true; pick.active = n ? (pick.active + 1) % n : -1 }
  else if (e.key === 'ArrowUp') { e.preventDefault(); pick.active = n ? (pick.active - 1 + n) % n : -1 }
  else if (e.key === 'Enter' && pick.open && pick.active >= 0) { e.preventDefault(); choose(i, options.value[pick.active]) }
  else if (e.key === 'Escape') { pick.open = false }
}
function link(i, item) {
  const p = points.value[i]
  p.mon_do_id = item.id
  if (!p.label_vi.trim() || p.label_vi === p.auto) p.label_vi = item.phan_loai || item.ten // never the supplier
  pick.open = false; pick.q = ''
}
const creating = reactive({ row: -1, ten: '', phan_loai: '', kieu_dang: '', vat_lieu: '', mau_sac: '', nha_cung_cap: '', dich_vu_id: null, error: '', busy: false })
const services = ref([])
itemServices().then(r => { services.value = r }).catch(() => {})
function choose(i, o) {
  if (o.id) return link(i, o)
  Object.assign(creating, { row: i, ten: o.ten, phan_loai: '', kieu_dang: '', vat_lieu: '', mau_sac: '', nha_cung_cap: '', dich_vu_id: null, error: '', busy: false })
  pick.open = false
}
async function createAndLink(i) {
  creating.busy = true; creating.error = ''
  const body = Object.fromEntries(['ten', 'phan_loai', 'kieu_dang', 'vat_lieu', 'mau_sac', 'nha_cung_cap']
    .map(k => [k, creating[k].trim() || null]).filter(([, v]) => v))
  if (creating.dich_vu_id) body.dich_vu_id = creating.dich_vu_id
  try {
    const item = await createItem(body)
    library.value = [...library.value, { ...item, so_anh: 0 }]
    link(i, item); creating.row = -1
  } catch (e) {
    creating.error = e.status === 409 ? `Đã có món đồ «${e.detail?.existing?.ten}». Hãy chọn món đó trong danh sách.` : e.message
  } finally { creating.busy = false }
}

async function save() {
  busy.value = true; error.value = ''
  for (const k of Object.keys(errors)) delete errors[k]
  const body = points.value.map(p => ({ ...(p.index !== null ? { index: p.index } : {}), x: p.x, y: p.y,
    label_vi: p.label_vi.trim(), mon_do_id: p.mon_do_id }))
  const empty = body.findIndex(p => !p.label_vi)
  if (empty >= 0) { errors[empty] = 'Đặt tên cho điểm này.'; busy.value = false; return focusName(empty) }
  try {
    const r = await saveHotspots(props.spaceId, body)
    emit('saved', r.hotspots)
  } catch (e) {
    const d = Array.isArray(e.detail) ? e.detail[0] : null
    if (d && d.loc?.[2] !== undefined && typeof d.loc[2] === 'number') { errors[d.loc[2]] = d.msg; focusName(d.loc[2]) }
    else error.value = d?.msg || e.message
  } finally { busy.value = false }
}
</script>

<style scoped>
.he { display: grid; gap: 10px; min-width: 0 }
.he-help { margin: 0; color: var(--dim) }
.he-stage { position: relative; cursor: crosshair; touch-action: none; user-select: none; max-width: 640px }
.he-stage img { display: block; width: 100%; height: auto; border-radius: var(--radius-sm); pointer-events: none }
.he-dot { position: absolute; transform: translate(-50%, -50%); width: 28px; height: 28px; border-radius: 50%; padding: 0;
  border: 2px solid #fff; background: var(--accent); color: var(--accent-on); font-size: 12px; cursor: grab;
  display: grid; place-items: center; box-shadow: 0 1px 6px rgba(0, 0, 0, .5); touch-action: none }
.he-dot.is-hand { background: var(--ink); color: var(--page) }
.he-dot.is-sel { outline: 3px solid var(--accent); outline-offset: 2px }
.he-dot:focus-visible { outline: 3px solid var(--ink); outline-offset: 2px }
.he-tools { align-items: center }
.he-rows { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px }
.he-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 6px; border-radius: var(--radius-sm) }
.he-row.is-sel { background: var(--line-soft) }
.he-n { width: 1.6em; text-align: right }
.he-chip { font-size: 11px; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--line); color: var(--dim) }
.he-chip.is-hand { border-color: var(--ink-2); color: var(--ink) }
.he-name { flex: 1 1 160px; min-width: 0 }
.he-pick { position: relative; flex: 1 1 200px; min-width: 0 }
.he-pick .txt { width: 100% }
.he-linked { display: flex; align-items: center; gap: 4px; padding: 6px 10px; border: 1px solid var(--line); border-radius: var(--radius-md) }
.he-linked span { flex: 1; min-width: 0; overflow-wrap: anywhere }
.he-x { padding: 2px 8px }
.he-lb { position: absolute; z-index: 5; left: 0; right: 0; top: calc(100% + 4px); list-style: none; margin: 0; padding: 4px;
  background: var(--page); border: 1px solid var(--line); border-radius: var(--radius-md); max-height: 240px; overflow-y: auto }
.he-lb li { padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer }
.he-lb li .small { color: var(--faint) }
.he-lb li.is-active, .he-lb li:hover { background: var(--line-soft) }
.he-empty { cursor: default; color: var(--faint) }
.he-err { flex-basis: 100% }
.he-new { flex-basis: 100%; display: grid; gap: 8px; padding: 10px; border: 1px dashed var(--line); border-radius: var(--radius-md) }
.he-grid { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 160px), 1fr)) }
.he-grid label { display: grid; gap: 4px; font-size: 12px; color: var(--dim) }
.he-wide { grid-column: 1 / -1 }
</style>
