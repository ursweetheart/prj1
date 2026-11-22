<template>
  <main class="wrap wrap-wide page-top" style="padding-bottom:clamp(28px,4vw,56px)">
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
        <p class="small num" aria-live="polite">{{ uploading ? `AI đã xử lý ${progress.done}/${progress.total} ảnh`
          : `Đã xử lý xong ${progress.ok} ảnh` }}</p>
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
      <button v-if="canReturn" class="btn btn-secondary" type="button" :disabled="!selected.size"
              @click="ask('return', [...selected], $event)">Trả về nháp {{ selected.size }} mục</button>
    </div>
    <!-- unpublish-photos: on "Đã đăng", the lead architect / admin can take photos down (with a reason) -->
    <div v-if="canUnpublish && rows.length" class="row g10" style="margin-top:16px;flex-wrap:wrap;align-items:center">
      <label class="row g10 small"><input type="checkbox" :checked="selected.size === rows.length" @change="selectAll($event.target.checked)"> Chọn tất cả</label>
      <button class="btn btn-secondary" type="button" :disabled="!selected.size"
              @click="ask('unpublish', [...selected], $event)">Gỡ khỏi website {{ selected.size }} mục</button>
    </div>
    <label v-if="status === 'draft'" class="row g10 small" style="margin-top:14px">
      <input v-model="onlyReturned" type="checkbox"> Chỉ ảnh bị trả về
    </label>
    <p v-if="moved" class="small" style="margin-top:12px" role="status">{{ moved }}</p>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!rows.length" class="small" style="margin-top:20px">{{ loading ? 'Đang tải…' : 'Không có không gian nào ở trạng thái này.' }}</p>

    <section v-for="g in groups" :key="g.project" style="margin-top:28px">
      <div class="row g10" style="flex-wrap:wrap;align-items:center">
        <label v-if="canSelect" class="row g10"><input type="checkbox" :checked="g.rows.every(r => selected.has(r.id))"
               @change="selectProject(g, $event.target.checked)" :aria-label="'Chọn cả dự án ' + g.project"></label>
        <h2 :id="'p-' + g.project" class="h-4 rv-anchor" style="margin:0">{{ g.project.replaceAll('_', ' ') }} <span class="small num">· {{ g.rows.length }}</span></h2>
        <template v-if="isStaff">
          <select v-for="d in humanDims" :key="d.id" class="txt" :value="projectTags[g.project + d.id] || ''" :aria-label="d.label + ' cho cả dự án'"
                  @change="projectTags[g.project + d.id] = $event.target.value">
            <option value="">{{ d.label }}…</option>
            <option v-for="o in d.options" :key="o.id" :value="o.id">{{ o.label }}</option>
          </select>
          <button class="btn btn-secondary" type="button" @click="tagProject(g)">Áp cho cả dự án</button>
        </template>
      </div>

      <ul class="stack" style="margin-top:12px;gap:14px;list-style:none;padding:0">
        <li v-for="r in g.rows" :key="r.id" class="form-ok" style="gap:16px;flex-wrap:wrap;align-items:flex-start">
          <input v-if="canSelect" type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id)" :aria-label="'Chọn ' + r.relative_path">
          <button type="button" class="thumb" :aria-label="'Sửa điểm nóng của ' + r.relative_path" :disabled="!isStaff" @click="openHotspots(r)">
            <img :srcset="imageSrcset(r) || null" sizes="200px" :src="imageUrl(r.relative_path)" :alt="r.alt_text" loading="lazy">
          </button>
          <div class="stack" style="flex:1;min-width:260px;gap:10px">
            <p class="small">{{ r.relative_path }}<template v-if="r.ngay_xuat_ban"> · Đăng ngày {{ dateVi(r.ngay_xuat_ban) }}</template></p>
            <p v-if="missing[r.id]" class="small rv-warn" role="alert">Thiếu: {{ missing[r.id].join(', ') }} (bắt buộc trước khi chuyển đi)</p>
            <p v-if="r.ly_do_duyet" class="rv-reason" :class="'is-' + r.ly_do_duyet.loai">
              <strong>{{ REASON_VI[r.ly_do_duyet.loai] }}</strong>
              <span class="rv-by">· {{ r.ly_do_duyet.boi }} · {{ when(r.ly_do_duyet.luc) }}</span><br>
              {{ r.ly_do_duyet.ly_do }}
            </p>
            <div v-if="isStaff" class="row g10" style="flex-wrap:wrap">
              <TagInput v-for="t in TYPED" :key="t.dim" v-model="r[t.col]" :values="tagValues[t.dim]" :id="t.dim + r.id"
                        :label="t.label + ' ' + r.id" :busy="!!suggesting[r.id + t.dim]" @suggest="suggest(r, t, $event)" />
              <select v-for="d in humanDims" :key="d.id" class="txt" :value="(r.tags[d.id] || [''])[0]" :aria-label="d.label + ' ' + r.id"
                      @change="tagOne(r, d.id, $event.target.value)">
                <option value="">{{ d.label }}…</option>
                <option v-for="o in d.options" :key="o.id" :value="o.id">{{ o.label }}</option>
              </select>
            </div>
            <!-- seq-1 b17: what the AI proposed, with its confidence; under 70% it says so in words, not colour alone -->
            <p v-if="isStaff && TYPED.some(t => r[t.ai])" class="small rv-ai">
              <span v-for="t in TYPED.filter(t => r[t.ai])" :key="'ai' + t.dim">
                {{ t.label }} AI: {{ nameOf(t.dim, r[t.ai]) }}<template v-if="r[t.conf] != null"> · <span class="num">{{ pct(r[t.conf]) }}%</span></template>
                <strong v-if="r[t.conf] != null && r[t.conf] < 0.7" class="rv-unsure">AI chưa chắc</strong>
              </span>
            </p>
            <template v-for="t in TYPED" :key="'s' + t.dim">
              <p v-if="offer[r.id + t.dim]" class="rv-offer" role="status">
                Có phải ý bạn là <strong>{{ nameOf(t.dim, offer[r.id + t.dim].ma) }}</strong>?
                <span v-if="offer[r.id + t.dim].ly_do" class="small">{{ offer[r.id + t.dim].ly_do }}</span>
                <button class="btn btn-secondary" type="button" @click="useOffer(r, t)">Dùng «{{ nameOf(t.dim, offer[r.id + t.dim].ma) }}»</button>
                <button class="btn btn-ghost" type="button" @click="suggest(r, t, offer[r.id + t.dim].text, true)">Vẫn gợi ý «{{ offer[r.id + t.dim].text }}»</button>
              </p>
              <p v-else-if="suggesting[r.id + t.dim]" class="small" role="status">Đang kiểm tra «{{ suggesting[r.id + t.dim] }}»…</p>
              <p v-if="warn[r.id + t.dim]" class="small rv-warn" role="status">⚠ {{ warn[r.id + t.dim] }}</p>
              <p v-if="r.cho_duyet_gia_tri?.[t.dim]" class="small rv-wait">
                {{ t.label }}: chờ KTS trưởng duyệt giá trị mới «{{ r.cho_duyet_gia_tri[t.dim] }}», tạm để «Khác»
              </p>
            </template>
            <p v-if="redrafted[r.id]" class="small rv-wait" role="status">
              AI đã soạn lại mô tả và alt text theo «{{ redrafted[r.id] }}». Sửa nếu cần rồi bấm Lưu.
            </p>
            <template v-if="canEditText">
              <div class="field"><label :for="'cap' + r.id">Mô tả</label>
                <textarea :id="'cap' + r.id" v-model="r.caption" rows="2"></textarea></div>
              <div class="field"><label :for="'alt' + r.id">Alt text (SEO)</label>
                <input :id="'alt' + r.id" v-model="r.alt_text"></div>
            </template>
            <p v-else class="small">{{ r.caption }}</p>
            <div v-if="isStaff" class="field"><label :for="'mat' + r.id">Vật liệu (cách nhau bằng dấu phẩy)</label>
              <input :id="'mat' + r.id" v-model="r.materialsText"></div>

            <HotspotEditor v-if="hs.id === r.id" :space-id="r.id" :src="imageUrl(r.relative_path)" :objects="hs.objects"
                           @saved="hs.id = null; saved = r.id" @close="hs.id = null" />

            <div class="row g10" style="flex-wrap:wrap">
              <button v-if="canEditText || isStaff" class="btn btn-secondary" type="button" @click="save(r)">Lưu</button>
              <!-- greyed until the photo is ticked: moving a photo on is a deliberate choice, not a stray click -->
              <button v-if="canAdvance && NEXT_STATUS[status] !== 'cleared'" class="btn btn-primary" type="button"
                      :disabled="!selected.has(r.id)" :title="selected.has(r.id) ? null : 'Tick chọn ảnh này trước'"
                      @click="advanceOne(r)">
                Chuyển sang «{{ STATUS_VI[NEXT_STATUS[status]] }}»
              </button>
              <template v-if="isApprover">
                <button v-if="RETURNABLE.includes(status)" class="btn btn-ghost" type="button" @click="ask('return', [r.id], $event)">Trả về nháp</button>
                <button v-if="status === 'approved' || status === 'cleared'" class="btn btn-ghost" type="button"
                        @click="ask('keep_internal', [r.id], $event)">Lưu nội bộ</button>
                <button v-if="status === 'noi_bo'" class="btn btn-secondary" type="button" @click="ask('reopen', [r.id], $event)">Mở lại</button>
                <button v-if="status === 'published'" class="btn btn-ghost" type="button" @click="ask('unpublish', [r.id], $event)">Gỡ khỏi website</button>
              </template>
              <span v-if="saved === r.id" class="small" aria-live="polite">Đã lưu</span>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- the reason for a backward move (seq-6 b9): required, shown on the card and sent to the uploader -->
    <dialog ref="dlgEl" class="rv-dialog" aria-labelledby="rv-dlg-h" @close="onDialogClose">
      <form v-if="dlg.action" class="stack" style="gap:12px" @submit.prevent="confirmMove">
        <h2 id="rv-dlg-h" class="h-4" style="margin:0">{{ ACTION_VI[dlg.action] }} · {{ dlg.ids.length }} ảnh</h2>
        <fieldset v-if="dlg.action === 'unpublish'" class="rv-outcome">
          <legend class="small">Sau khi gỡ</legend>
          <label class="row g10"><input v-model="dlg.internal" type="radio" name="rv-outcome" :value="false"> Gỡ xuống để sửa (về Nháp)</label>
          <label class="row g10"><input v-model="dlg.internal" type="radio" name="rv-outcome" :value="true"> Gỡ và lưu nội bộ (khách rút lại đồng ý)</label>
        </fieldset>
        <div class="field">
          <label for="rv-reason">Lý do <span class="small">(bắt buộc, người tải ảnh lên sẽ nhận được)</span></label>
          <textarea id="rv-reason" v-model="dlg.reason" rows="3" maxlength="500" required
                    :aria-invalid="!!dlg.error" aria-describedby="rv-count rv-err"></textarea>
          <span id="rv-count" class="small num">{{ dlg.reason.trim().length }}/500</span>
          <span v-if="dlg.error" id="rv-err" class="small" style="color:var(--danger)" role="alert">{{ dlg.error }}</span>
        </div>
        <div class="row g10">
          <button class="btn btn-primary" :disabled="dlg.busy">{{ dlg.busy ? 'Đang chuyển…' : 'Xác nhận' }}</button>
          <button class="btn btn-ghost" type="button" @click="dlgEl.close()">Huỷ</button>
        </div>
      </form>
    </dialog>
  </main>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  APPROVERS, NEXT_STATUS, RETURNABLE, imageSrcset, STAFF, STATUS_VI, advanceSpaces, getSpace, getTaxonomy, hasRole,
  imageUrl, keepInternal, listSpaces, projectOf, reopenSpaces, returnSpaces, reviewSpace, setTags, suggestValue, toFacet, unpublishSpaces,
  uploadAll
} from '@/api'
import HotspotEditor from '@/components/HotspotEditor.vue'
import TagInput from '@/components/TagInput.vue'

const HUMAN = ['loai_cong_trinh', 'muc_dau_tu'] // the AI cannot see these; staff fill them per project

/* /quan-tri#p-<folder> (from the project results page): open the published tab and scroll to that project */
const route = useRoute()
const target = ref(route.hash.startsWith('#p-') ? decodeURIComponent(route.hash.slice(3)) : '')
const status = ref(target.value ? 'published' : 'draft')
const rows = ref([])
const loading = ref(false)
const error = ref('')
const saved = ref(null)
const humanDims = ref([])
const tagValues = reactive({ khong_gian: [], phong_cach: [] }) // typed with suggestions (review-tag-autocomplete)
const TYPED = [{ dim: 'khong_gian', col: 'space_type', label: 'Loại không gian', other: 'khac', ai: 'space_type_ai', conf: 'space_type_confidence' },
  { dim: 'phong_cach', col: 'design_style', label: 'Phong cách', other: 'Khac', ai: 'design_style_ai', conf: 'style_confidence' }]
const pct = x => Math.round(100 * x)
const nameOf = (dim, code) => tagValues[dim].find(v => v.ma_dinh_danh === code)?.ten || code
const suggesting = reactive({}) // `${space id}${dim}` -> word being checked
const offer = reactive({}) // `${space id}${dim}` -> { ma, ly_do, text }: "Did you mean …?"
const warn = reactive({}) // `${space id}${dim}` -> the AI thinks this photo doesn't show the suggested word
const redrafted = reactive({}) // space id -> word the AI rewrote the caption for (unsaved)

/* A word that names no stored value: the server tries spelling, then Gemini, then saves it for the lead architect.
   force: the reviewer saw the offer and still wants their word. */
const suggest = (r, t, text, force = false) => run(async () => {
  const k = r.id + t.dim
  delete offer[k]; delete warn[k]; suggesting[k] = text
  try {
    const out = await suggestValue(r.id, t.dim, text, force)
    if (out.kind === 'existing' && out.source === 'exact') r[t.col] = out.ma
    else if (out.kind === 'existing') offer[k] = { ma: out.ma, ly_do: out.ly_do || '', text }
    else {
      r[t.col] = t.other; r.cho_duyet_gia_tri = { ...(r.cho_duyet_gia_tri || {}), [t.dim]: text }
      if (out.canh_bao) warn[k] = out.canh_bao + (out.gan_nhat ? ` Gần nhất: «${nameOf(t.dim, out.gan_nhat)}».` : '')
      if (out.caption) { // drafted in the same Gemini call; only saved when the reviewer clicks Lưu
        r.caption = out.caption
        if (out.alt_text) r.alt_text = out.alt_text
        redrafted[r.id] = text
      }
    }
  } finally { delete suggesting[k] }
})
const useOffer = (r, t) => { r[t.col] = offer[r.id + t.dim].ma; delete offer[r.id + t.dim] }

const isStaff = computed(() => hasRole(STAFF))
// architects send drafts to review; only the lead architect approves, clears and publishes
const canAdvance = computed(() => status.value in NEXT_STATUS && (status.value === 'draft' ? isStaff.value
  : status.value === 'editing' ? hasRole(['content', ...APPROVERS]) : hasRole(APPROVERS)))
const canEditText = computed(() => isStaff.value || (hasRole(['content']) && ['editing', 'in_review'].includes(status.value)))

const groups = computed(() => {
  const by = {}
  rows.value.forEach(r => (by[projectOf(r.relative_path)] ||= []).push(r))
  return Object.entries(by).map(([project, list]) => ({ project, rows: list }))
})

async function load() {
  loading.value = true; error.value = ''; selected.clear(); hs.id = null; moved.value = ''
  try {
    // every page: the API returns at most 200 rows, and new uploads have the highest ids (seq-1 b17 must reach them)
    const params = { review_status: status.value, ...(status.value === 'draft' && onlyReturned.value ? { tra_ve: 1 } : {}) }
    const all = []
    for (let page; (page = await listSpaces({ ...params, limit: 200, offset: all.length })).length;) {
      all.push(...page)
      if (page.length < 200) break
    }
    rows.value = all.map(r => ({ ...r, materialsText: (r.materials || []).join(', ') }))
  } catch (e) { error.value = e.message; rows.value = [] }
  finally { loading.value = false }
  if (target.value) {
    await nextTick()
    const h = document.getElementById('p-' + target.value)
    if (h) { h.scrollIntoView({ block: 'start' }); h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }) }
    target.value = ''
  }
}

const missing = reactive({}) // space id -> required dimensions it lacks (act-1 "Đủ các features bắt buộc?")
async function run(fn) {
  error.value = ''
  try { await fn() } catch (e) {
    error.value = e.message
    if (e.detail?.thieu) missing[e.detail.space_id] = e.detail.thieu // shown on that photo's card too
  }
}
const dateVi = iso => new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

/* ── upload ─────────────────────────────────────────────────────────── */
const project = ref('')
const files = ref([])
const fileInput = ref(null)
const uploading = ref(false)
const progress = reactive({ done: 0, total: 0, ok: 0 })
const failed = ref([])

/* seq-1: the server queues the photos and answers at once; the queue is followed until every photo is done (b16) */
async function upload() {
  uploading.value = true; failed.value = []
  Object.assign(progress, { done: 0, total: files.value.length, ok: 0 })
  try {
    const r = await uploadAll(files.value, project.value, (n, total) => Object.assign(progress, { done: n, total }))
    progress.ok = r.ok; failed.value = r.failed
  } catch (e) { failed.value = [{ name: 'Tải lên', error: e.message }] }
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
  return run(async () => { await reviewSpace(r.id, body); saved.value = r.id; delete redrafted[r.id] })
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
  hs.objects = (s.hotspots && s.hotspots.objects) || [] // HotspotEditor saves through PUT /spaces/{id}/hotspots
  hs.id = r.id
})

/* ── advance ────────────────────────────────────────────────────────── */
const selected = reactive(new Set())
const rightsConfirmed = ref(false)
const toggle = id => (selected.has(id) ? selected.delete(id) : selected.add(id))
const selectAll = on => { selected.clear(); if (on) rows.value.forEach(r => selected.add(r.id)) }
const selectProject = (g, on) => g.rows.forEach(r => (on ? selected.add(r.id) : selected.delete(r.id)))

const advanceOne = r => run(async () => {
  delete missing[r.id]
  await reviewSpace(r.id, { advance: true })
  rows.value = rows.value.filter(x => x.id !== r.id)
})

const advanceSelected = () => run(async () => {
  await advanceSpaces([...selected], rightsConfirmed.value)
  rightsConfirmed.value = false
  await load()
})

/* ── backward paths: return to draft, keep internal, reopen (review-return-reject) ── */
const isApprover = computed(() => hasRole(APPROVERS))
const canReturn = computed(() => isApprover.value && RETURNABLE.includes(status.value))
const canUnpublish = computed(() => isApprover.value && status.value === 'published')
const canSelect = computed(() => canAdvance.value || canUnpublish.value)
const onlyReturned = ref(false)
const moved = ref('')
const REASON_VI = { tra_ve: 'Bị trả về', noi_bo: 'Lưu nội bộ', mo_lai: 'Mở lại', go_xuong: 'Đã gỡ khỏi website',
  go_noi_bo: 'Gỡ khỏi website, lưu nội bộ' }
const ACTION_VI = { return: 'Trả về nháp', keep_internal: 'Lưu nội bộ, không xuất bản', reopen: 'Mở lại về nháp',
  unpublish: 'Gỡ khỏi website' }
const CALL = { return: returnSpaces, keep_internal: keepInternal, reopen: reopenSpaces,
  unpublish: (ids, reason) => unpublishSpaces(ids, reason, dlg.internal) }
const when = t => (t ? new Date(t).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : '')
const dlgEl = ref(null)
const dlg = reactive({ action: '', ids: [], reason: '', error: '', busy: false, opener: null, internal: false })

function ask(action, ids, e) {
  Object.assign(dlg, { action, ids, reason: '', error: '', busy: false, opener: e?.currentTarget || null, internal: false })
  nextTick(() => { dlgEl.value.showModal(); document.getElementById('rv-reason')?.focus() })
}
function onDialogClose() {
  const back = dlg.opener
  dlg.action = ''
  if (back?.isConnected) back.focus() // Esc / Huỷ: focus returns to the button that opened the dialog
}
async function confirmMove() {
  const reason = dlg.reason.trim()
  if (reason.length < 5) { dlg.error = 'Lý do cần ít nhất 5 ký tự.'; return }
  dlg.busy = true; dlg.error = ''
  try {
    const out = await CALL[dlg.action](dlg.ids, reason)
    const n = out.moved.length
    dlg.opener = null // the card is gone; focus stays on the page
    dlgEl.value.close()
    moved.value = `Đã chuyển ${n} ảnh sang «${STATUS_VI[out.status]}».`
    rows.value = rows.value.filter(r => !out.moved.includes(r.id))
    out.moved.forEach(id => selected.delete(id))
  } catch (e) {
    dlg.error = typeof e.detail === 'string' ? e.detail : Array.isArray(e.detail) ? e.detail.map(x => x.msg).join('; ') : e.message
  } finally { dlg.busy = false }
}

watch(onlyReturned, load)
watch(status, load, { immediate: true })
getTaxonomy()
  .then(dims => {
    humanDims.value = dims.filter(d => HUMAN.includes(d.ma_dinh_danh)).map(toFacet)
    for (const d of dims) if (d.ma_dinh_danh in tagValues) tagValues[d.ma_dinh_danh] = d.values
  })
  .catch(() => {}) // without the taxonomy the tag selects just stay hidden
</script>

<style scoped>
.rv-anchor { scroll-margin-top: 232px } /* below the fixed header, as .page-top */
@media (min-width: 1024px) { .rv-anchor { scroll-margin-top: 128px } }
.panel { border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px }
.thumb { padding: 0; border: 0; background: none; cursor: pointer; border-radius: var(--radius-sm); overflow: hidden }
.thumb img { width: 140px; height: 100px; object-fit: cover; display: block }
.thumb:disabled { cursor: default }
.rv-reason { margin: 0; padding: 8px 12px; border-left: 3px solid var(--warn); background: var(--panel); font-size: 14px;
  color: var(--ink); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; overflow-wrap: anywhere }
.rv-reason.is-noi_bo, .rv-reason.is-go_noi_bo { border-left-color: var(--danger) }
.rv-outcome { border: 1px solid var(--line); border-radius: var(--radius-md); padding: 10px 12px; margin: 0; display: grid; gap: 6px }
.rv-outcome legend { padding: 0 4px; color: var(--dim) }
.rv-outcome input { accent-color: var(--accent) }
.rv-reason.is-mo_lai { border-left-color: var(--success) }
.rv-offer { margin: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px }
.rv-offer .small { flex-basis: 100%; color: var(--dim) }
.rv-wait { margin: 0; color: var(--warn) }
.rv-ai { margin: 0; display: flex; flex-wrap: wrap; gap: 4px 16px; color: var(--dim) }
.rv-unsure { margin-left: 6px; color: var(--warn); font-weight: 600 }
.rv-warn { margin: 0; color: var(--danger) }
.rv-by { color: var(--dim); font-size: 13px }
.rv-dialog { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--page); color: var(--ink);
  padding: 20px; width: min(520px, calc(100vw - 32px)) }
.rv-dialog::backdrop { background: rgba(0, 0, 0, 0.55) }
.rv-dialog textarea { width: 100%; background: var(--panel); color: var(--ink); border: 1px solid var(--line);
  border-radius: var(--radius-md); padding: 10px 12px; font: inherit; color-scheme: dark }
</style>
