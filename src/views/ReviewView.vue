<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Duyệt không gian</h1>
    <p class="lead" style="margin-top:10px">AI gán nhãn ở trạng thái nháp; kiến trúc sư xác nhận, content biên tập lời, KTS trưởng duyệt và đăng.</p>

    <!-- Tải ảnh của một dự án (QT-01 bước 1) -->
    <form v-if="isStaff" class="panel stack" style="margin-top:24px;gap:12px" @submit.prevent="upload">
      <span class="h-4">Tải ảnh dự án mới</span>
      <div class="row g10" style="flex-wrap:wrap;align-items:flex-end">
        <div class="field" style="flex:1;min-width:220px">
          <label for="project">Tên dự án</label>
          <input id="project" v-model="project" required placeholder="vd: Biệt thự Thảo Điền" :disabled="uploading">
        </div>
        <div class="field" style="flex:1;min-width:220px">
          <label for="files">Ảnh (jpg, png, webp)</label>
          <input id="files" ref="fileInput" type="file" multiple accept=".jpg,.jpeg,.png,.webp" required :disabled="uploading"
                 @change="files = $event.target.files">
        </div>
        <button class="btn btn-primary" type="submit" :disabled="uploading">{{ uploading ? 'Đang xử lý…' : 'Tải lên' }}</button>
      </div>
      <template v-if="progress.total">
        <progress :value="progress.done" :max="progress.total" style="width:100%"></progress>
        <p class="small num" aria-live="polite">AI đã xử lý {{ progress.done }}/{{ progress.total }} ảnh</p>
      </template>
      <ul v-if="failed.length" class="small" style="color:var(--danger);margin:0" role="alert">
        <li v-for="f in failed" :key="f.name">{{ f.name }}: {{ f.error }}</li>
      </ul>
    </form>

    <div class="row g10" style="margin-top:24px;flex-wrap:wrap">
      <button v-for="(label, key) in STATUS_VI" :key="key" type="button" class="chip"
              :aria-pressed="String(status === key)" @click="status = key">{{ label }}</button>
    </div>

    <!-- Chuyển hàng loạt -->
    <div v-if="canAdvance && rows.length" class="row g10" style="margin-top:16px;flex-wrap:wrap;align-items:center">
      <label class="row g10 small"><input type="checkbox" :checked="selected.size === rows.length" @change="selectAll($event.target.checked)"> Chọn tất cả</label>
      <label v-if="NEXT_STATUS[status] === 'cleared'" class="row g10 small">
        <input v-model="rightsConfirmed" type="checkbox"> Khách hàng đã đồng ý cho công bố các ảnh này
      </label>
      <button class="btn btn-primary" type="button" :disabled="!selected.size || (NEXT_STATUS[status] === 'cleared' && !rightsConfirmed)"
              @click="advanceSelected">
        Chuyển {{ selected.size }} mục sang «{{ STATUS_VI[NEXT_STATUS[status]] }}»
      </button>
    </div>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!rows.length" class="small" style="margin-top:20px">{{ loading ? 'Đang tải…' : 'Không có không gian nào ở trạng thái này.' }}</p>

    <section v-for="g in groups" :key="g.project" style="margin-top:28px">
      <div class="row g10" style="flex-wrap:wrap;align-items:center">
        <label v-if="canAdvance" class="row g10"><input type="checkbox" :checked="g.rows.every(r => selected.has(r.id))"
               @change="selectProject(g, $event.target.checked)" :aria-label="'Chọn cả dự án ' + g.project"></label>
        <h2 class="h-4" style="margin:0">{{ g.project.replaceAll('_', ' ') }} <span class="small num">· {{ g.rows.length }}</span></h2>
        <template v-if="isStaff">
          <select v-for="d in humanDims" :key="d.id" :value="projectTags[g.project + d.id] || ''" :aria-label="d.label + ' cho cả dự án'"
                  @change="projectTags[g.project + d.id] = $event.target.value">
            <option value="">{{ d.label }}…</option>
            <option v-for="o in d.options" :key="o.id" :value="o.id">{{ o.label }}</option>
          </select>
          <button class="btn btn-secondary" type="button" @click="tagProject(g)">Áp cho cả dự án</button>
        </template>
      </div>

      <ul class="stack" style="margin-top:12px;gap:14px;list-style:none;padding:0">
        <li v-for="r in g.rows" :key="r.id" class="form-ok" style="gap:16px;flex-wrap:wrap;align-items:flex-start">
          <input v-if="canAdvance" type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id)" :aria-label="'Chọn ' + r.relative_path">
          <button type="button" class="thumb" :aria-label="'Sửa điểm nóng của ' + r.relative_path" :disabled="!isStaff" @click="openHotspots(r)">
            <img :src="imageUrl(r.relative_path)" :alt="r.alt_text" loading="lazy">
          </button>
          <div class="stack" style="flex:1;min-width:260px;gap:10px">
            <p class="small">{{ r.relative_path }}</p>
            <div v-if="isStaff" class="row g10" style="flex-wrap:wrap">
              <select v-model="r.space_type" :aria-label="'Loại không gian ' + r.id">
                <option v-for="t in SPACE_TYPES" :key="t" :value="t">{{ spaceLabel(t) }}</option>
              </select>
              <select v-model="r.design_style" :aria-label="'Phong cách ' + r.id">
                <option v-for="s in STYLES" :key="s" :value="s">{{ s.replaceAll('_', ' ') }}</option>
              </select>
              <select v-for="d in humanDims" :key="d.id" :value="(r.tags[d.id] || [''])[0]" :aria-label="d.label + ' ' + r.id"
                      @change="tagOne(r, d.id, $event.target.value)">
                <option value="">{{ d.label }}…</option>
                <option v-for="o in d.options" :key="o.id" :value="o.id">{{ o.label }}</option>
              </select>
            </div>
            <template v-if="canEditText">
              <div class="field"><label :for="'cap' + r.id">Mô tả</label>
                <textarea :id="'cap' + r.id" v-model="r.caption" rows="2"></textarea></div>
              <div class="field"><label :for="'alt' + r.id">Alt text (SEO)</label>
                <input :id="'alt' + r.id" v-model="r.alt_text"></div>
            </template>
            <p v-else class="small">{{ r.caption }}</p>
            <div v-if="isStaff" class="field"><label :for="'mat' + r.id">Vật liệu (cách nhau bằng dấu phẩy)</label>
              <input :id="'mat' + r.id" v-model="r.materialsText"></div>

            <div v-if="hs.id === r.id" class="stack" style="gap:8px">
              <div class="hs-edit">
                <img :src="imageUrl(r.relative_path)" alt="">
                <span v-for="(o, i) in hs.objects" :key="o.index" class="dot"
                      :style="{ left: o.hotspot_anchor[0] * 100 + '%', top: o.hotspot_anchor[1] * 100 + '%' }">{{ i + 1 }}</span>
              </div>
              <p v-if="!hs.objects.length" class="small">Không còn điểm nóng nào.</p>
              <div v-for="(o, i) in hs.objects" :key="o.index" class="row g10">
                <span class="num small">{{ i + 1 }}</span>
                <input v-model="o.label_vi" class="txt" style="flex:1" :aria-label="'Tên món đồ ' + (i + 1)">
                <button class="btn btn-ghost" type="button" @click="hs.objects.splice(i, 1)">Xoá</button>
              </div>
              <div class="row g10">
                <button class="btn btn-secondary" type="button" @click="saveHotspots(r)">Lưu điểm nóng</button>
                <button class="btn btn-ghost" type="button" @click="hs.id = null">Đóng</button>
              </div>
            </div>

            <div class="row g10" style="flex-wrap:wrap">
              <button v-if="canEditText || isStaff" class="btn btn-secondary" type="button" @click="save(r)">Lưu</button>
              <button v-if="canAdvance && NEXT_STATUS[status] !== 'cleared'" class="btn btn-primary" type="button" @click="advanceOne(r)">
                Chuyển sang «{{ STATUS_VI[NEXT_STATUS[status]] }}»
              </button>
              <span v-if="saved === r.id" class="small" aria-live="polite">Đã lưu</span>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </main>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  APPROVERS, NEXT_STATUS, SPACE_TYPES, STAFF, STATUS_VI, STYLES, advanceSpaces, getSpace, getTaxonomy, hasRole,
  imageUrl, listSpaces, projectOf, reviewSpace, setTags, spaceLabel, toFacet, uploadAll
} from '@/api'

const HUMAN = ['loai_cong_trinh', 'muc_dau_tu'] // the AI cannot see these; staff fill them per project

const status = ref('draft')
const rows = ref([])
const loading = ref(false)
const error = ref('')
const saved = ref(null)
const humanDims = ref([])

const isStaff = computed(() => hasRole(STAFF))
// architects send drafts to review; only the lead architect approves, clears and publishes
const canAdvance = computed(() => status.value in NEXT_STATUS && (status.value === 'draft' ? isStaff.value : hasRole(APPROVERS)))
const canEditText = computed(() => isStaff.value || (hasRole(['content']) && status.value === 'in_review'))

const groups = computed(() => {
  const by = {}
  rows.value.forEach(r => (by[projectOf(r.relative_path)] ||= []).push(r))
  return Object.entries(by).map(([project, list]) => ({ project, rows: list }))
})

async function load() {
  loading.value = true; error.value = ''; selected.clear(); hs.id = null
  try {
    rows.value = (await listSpaces({ review_status: status.value }))
      .map(r => ({ ...r, materialsText: (r.materials || []).join(', ') }))
  } catch (e) { error.value = e.message; rows.value = [] }
  finally { loading.value = false }
}

async function run(fn) {
  error.value = ''
  try { await fn() } catch (e) { error.value = e.message }
}

/* ── upload ─────────────────────────────────────────────────────────── */
const project = ref('')
const files = ref([])
const fileInput = ref(null)
const uploading = ref(false)
const progress = reactive({ done: 0, total: 0 })
const failed = ref([])

async function upload() {
  uploading.value = true; failed.value = []
  progress.done = 0; progress.total = files.value.length
  failed.value = await uploadAll(files.value, project.value, n => { progress.done = n })
  uploading.value = false
  fileInput.value.value = ''
  if (status.value === 'draft') load(); else status.value = 'draft' // new spaces start as drafts
}

/* ── edit ───────────────────────────────────────────────────────────── */
function save(r) {
  const body = isStaff.value
    ? { space_type: r.space_type, design_style: r.design_style, caption: r.caption, alt_text: r.alt_text,
        materials: r.materialsText.split(',').map(m => m.trim()).filter(Boolean) }
    : { caption: r.caption, alt_text: r.alt_text }
  return run(async () => { await reviewSpace(r.id, body); saved.value = r.id })
}

const tagOne = (r, dimension, value) => run(async () => {
  await setTags({ space_ids: [r.id], dimension, values: value ? [value] : [] })
  r.tags = { ...r.tags, [dimension]: value ? [value] : [] }
})

const projectTags = reactive({})
const tagProject = g => run(async () => {
  for (const d of humanDims.value) {
    const value = projectTags[g.project + d.id]
    if (!value) continue
    await setTags({ project: g.project, dimension: d.id, values: [value] })
    g.rows.forEach(r => { r.tags = { ...r.tags, [d.id]: [value] } })
  }
})

/* ── hotspots ───────────────────────────────────────────────────────── */
const hs = reactive({ id: null, objects: [] })

const openHotspots = r => run(async () => {
  const s = await getSpace(r.id)
  hs.objects = ((s.hotspots && s.hotspots.objects) || []).map((o, index) => ({ ...o, index, label_vi: o.label_vi || o.label }))
  hs.id = r.id
})

const saveHotspots = r => run(async () => {
  await reviewSpace(r.id, { hotspots: hs.objects.map(o => ({ index: o.index, label_vi: o.label_vi })) })
  hs.id = null; saved.value = r.id
})

/* ── advance ────────────────────────────────────────────────────────── */
const selected = reactive(new Set())
const rightsConfirmed = ref(false)
const toggle = id => (selected.has(id) ? selected.delete(id) : selected.add(id))
const selectAll = on => { selected.clear(); if (on) rows.value.forEach(r => selected.add(r.id)) }
const selectProject = (g, on) => g.rows.forEach(r => (on ? selected.add(r.id) : selected.delete(r.id)))

const advanceOne = r => run(async () => {
  await reviewSpace(r.id, { advance: true })
  rows.value = rows.value.filter(x => x.id !== r.id)
})

const advanceSelected = () => run(async () => {
  await advanceSpaces([...selected], rightsConfirmed.value)
  rightsConfirmed.value = false
  await load()
})

watch(status, load, { immediate: true })
getTaxonomy()
  .then(dims => { humanDims.value = dims.filter(d => HUMAN.includes(d.ma_dinh_danh)).map(toFacet) })
  .catch(() => {}) // without the taxonomy the tag selects just stay hidden
</script>

<style scoped>
select, .txt { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 10px 12px; min-height: 42px; max-width: 100%; color-scheme: dark }
select:focus-visible, .txt:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring) }
.panel { border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px }
.thumb { padding: 0; border: 0; background: none; cursor: pointer; border-radius: var(--radius-sm); overflow: hidden }
.thumb img { width: 140px; height: 100px; object-fit: cover; display: block }
.thumb:disabled { cursor: default }
.hs-edit { position: relative; max-width: 520px }
.hs-edit img { width: 100%; display: block; border-radius: var(--radius-sm) }
.dot { position: absolute; transform: translate(-50%, -50%); width: 24px; height: 24px; border-radius: 50%;
  background: var(--accent); color: var(--accent-on); font-size: 12px; display: grid; place-items: center }
</style>
