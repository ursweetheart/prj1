<template>
  <main class="wrap wrap-wide page-top kn-page">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Tri thức trợ lý</h1>
    <p class="lead" style="margin-top:10px">
      Trợ lý chỉ trả lời từ các mục «Đang dùng». Mục có giá chỉ được bật sau khi KTS trưởng duyệt.
    </p>

    <div class="kn-tabs" role="tablist" aria-label="Tri thức trợ lý" @keydown="onTabKey">
      <button v-for="t in TABS" :id="'kt-' + t.id" :key="t.id" ref="tabEls" type="button" role="tab" class="kn-tab"
              :aria-selected="String(tab === t.id)" :aria-controls="'kp-' + t.id" :tabindex="tab === t.id ? 0 : -1"
              @click="select(t.id)">{{ t.label }}<span v-if="t.id === 'cau-hoi' && gapCount" class="num"> ({{ gapCount }})</span></button>
    </div>
    <p v-if="note" class="kn-note" role="status">{{ note }}</p>
    <p v-if="error" class="field-err" role="alert">{{ error }}</p>

    <!-- ── entries ── -->
    <section v-show="tab === 'muc'" id="kp-muc" role="tabpanel" aria-labelledby="kt-muc">
      <div class="kn-bar">
        <label class="sr-only" for="kn-q">Tìm mục tri thức</label>
        <input id="kn-q" v-model="q" class="txt kn-search" type="search" placeholder="Tìm theo tiêu đề, cụm từ, nội dung"
               @input="reloadSoon">
        <button class="btn btn-primary" type="button" @click="startNew()">+ Mục mới</button>
      </div>
      <div class="kn-chips" role="group" aria-label="Lọc theo trạng thái">
        <button type="button" class="chip" :aria-pressed="String(!filter)" @click="setFilter('')">Tất cả</button>
        <button v-for="(label, k) in STATUS" :key="k" type="button" class="chip" :aria-pressed="String(filter === k)"
                @click="setFilter(k)">{{ label }} <span class="num">{{ dem[k] ?? 0 }}</span></button>
      </div>

      <!-- new entry -->
      <form v-if="editing === 'new'" class="kn-editor" @submit.prevent="saveNew('nhap')">
        <h2 class="h-4" style="margin:0">Mục mới</h2>
        <p v-if="form.tu_cau_hoi.length" class="small">Soạn từ {{ form.tu_cau_hoi.length }} câu hỏi chưa trả lời; các câu này đóng khi mục được bật.</p>
        <EntryFields :form="form" :errors="fieldErr" id-prefix="new" />
        <div class="row g10 kn-actions">
          <button class="btn btn-secondary" :disabled="busy">Lưu nháp</button>
          <button v-if="priceBlocked(form)" class="btn btn-primary" type="button" :disabled="busy" @click="saveNew('cho_duyet')">
            Gửi KTS trưởng duyệt</button>
          <button v-else class="btn btn-primary" type="button" :disabled="busy" @click="saveNew('on')">Lưu và bật sử dụng</button>
          <button class="btn btn-ghost" type="button" @click="closeEditor">Huỷ</button>
        </div>
        <p v-if="priceBlocked(form)" class="small">Câu trả lời có giá: KTS trưởng cần duyệt trước khi trợ lý được nêu.</p>
      </form>

      <p v-if="loading && !items.length" class="small">Đang tải…</p>
      <p v-else-if="!items.length" class="small">Không có mục nào.</p>
      <ul class="kn-list">
        <li v-for="e in items" :key="e.id" class="kn-item">
          <button type="button" class="kn-row" :aria-expanded="String(editing === e.id)" :aria-controls="'ke-' + e.id"
                  @click="toggleEdit(e)">
            <span class="kn-title">{{ e.title }}</span>
            <span class="kn-badges">
              <span class="kn-badge" :class="'is-' + e.trang_thai">{{ STATUS[e.trang_thai] }}</span>
              <span class="kn-badge">{{ KIND[e.kind] }}</span>
              <span v-if="e.can_duyet_gia" class="kn-badge is-price">Có giá</span>
              <span v-if="e.mau" class="kn-badge is-sample">Dữ liệu mẫu</span>
              <span v-if="e.ai" class="kn-badge is-ai">AI soạn</span>
            </span>
            <span class="kn-excerpt">{{ e.content }}</span>
          </button>

          <form v-if="editing === e.id" :id="'ke-' + e.id" class="kn-editor" @submit.prevent="saveEdit(e)">
            <EntryFields :form="form" :errors="fieldErr" :id-prefix="'e' + e.id" :title-locked="e.lien_ket" />
            <p class="small kn-meta">
              Nguồn: {{ SOURCE[e.nguon] || e.nguon || '—' }} · sửa lần cuối {{ when(e.updated_at) }}{{ e.updated_by ? ' bởi ' + e.updated_by : '' }}
            </p>
            <div class="row g10 kn-actions">
              <button class="btn btn-secondary" :disabled="busy">Lưu</button>
              <template v-if="e.trang_thai !== 'dang_dung'">
                <button v-if="priceBlocked(e) && e.trang_thai !== 'cho_duyet'" class="btn btn-primary" type="button" :disabled="busy"
                        @click="move(e, 'cho_duyet')">Gửi KTS trưởng duyệt</button>
                <button v-else-if="!priceBlocked(e)" class="btn btn-primary" type="button" :disabled="busy"
                        @click="move(e, 'dang_dung')">{{ e.trang_thai === 'cho_duyet' && isApprover ? 'Duyệt và bật' : 'Bật sử dụng' }}</button>
              </template>
              <button v-if="e.trang_thai === 'dang_dung'" class="btn btn-ghost" type="button" :disabled="busy" @click="move(e, 'tat')">Tắt</button>
              <button v-if="e.trang_thai !== 'nhap'" class="btn btn-ghost" type="button" :disabled="busy" @click="move(e, 'nhap')">Về nháp</button>
              <button v-if="isApprover" class="btn btn-ghost kn-danger" type="button" :disabled="busy || e.lien_ket"
                      :title="e.lien_ket ? 'Điểm nóng đang liên kết tới mục này' : null" @click="askDelete(e, $event)">Xoá</button>
              <button class="btn btn-ghost" type="button" @click="closeEditor">Đóng</button>
            </div>
            <p v-if="priceBlocked(e) && e.trang_thai === 'cho_duyet'" class="small">Đang chờ KTS trưởng duyệt (mục có giá).</p>
            <p v-if="e.lien_ket" class="small">Điểm nóng trên ảnh liên kết tới mục này nên không đổi tên hay xoá được; vẫn sửa được nội dung.</p>
          </form>
        </li>
      </ul>
    </section>

    <!-- ── unanswered questions ── -->
    <section v-show="tab === 'cau-hoi'" id="kp-cau-hoi" role="tabpanel" aria-labelledby="kt-cau-hoi">
      <p class="small" style="margin-top:0">Câu khách hỏi mà trợ lý chưa trả lời được, gom các câu giống nhau, hỏi nhiều nhất lên trước.</p>
      <p v-if="!gaps.length" class="small">Không còn câu hỏi nào đang mở.</p>
      <ul class="kn-list">
        <li v-for="g in gaps" :key="g.ids[0]" class="kn-gap">
          <p class="kn-gap-q">“{{ g.cau_hoi }}”</p>
          <p class="small num">×{{ g.so_lan }} · lần cuối {{ when(g.lan_cuoi) }}</p>
          <p v-if="g.tu_chua_khop.length" class="kn-terms">
            <span class="sr-only">Từ chưa có trong phân loại:</span>
            <span v-for="t in g.tu_chua_khop" :key="t" class="kn-badge">{{ t }}</span>
          </p>
          <div class="row g10">
            <button class="btn btn-secondary" type="button" @click="answerGap(g)">Soạn đáp án</button>
            <button class="btn btn-ghost" type="button" :disabled="busy" @click="dismiss(g)">Bỏ qua</button>
          </div>
        </li>
      </ul>
    </section>

    <dialog ref="delEl" class="kn-dialog" aria-labelledby="kn-del-h" @close="onDelClose">
      <form v-if="deleting" class="stack" style="gap:12px" @submit.prevent="doDelete">
        <h2 id="kn-del-h" class="h-4" style="margin:0">Xoá «{{ deleting.title }}»?</h2>
        <p class="small" style="margin:0">Trợ lý sẽ không dùng mục này nữa. Không hoàn tác được; nhật ký vẫn giữ nội dung đã xoá.</p>
        <div class="row g10">
          <button class="btn btn-primary" :disabled="busy">Xoá</button>
          <button class="btn btn-ghost" type="button" @click="delEl.close()">Huỷ</button>
        </div>
      </form>
    </dialog>
  </main>
</template>

<script setup>
/* /quan-tri/tri-thuc (NV nội dung, KTS trưởng, admin): what the chatbot answers from (UC16, seq-16), and the
 * questions it could not answer. The server enforces the price rule; the buttons only follow it. */
import { computed, defineComponent, h, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APPROVERS, createKnowledge, deleteKnowledge, dismissGaps, hasRole, knowledgeGaps, listKnowledge,
  setKnowledgeStatus, updateKnowledge } from '@/api'
import { needsPriceApproval } from '@/lib/priceRule'

const STATUS = { nhap: 'Nháp', cho_duyet: 'Chờ duyệt', dang_dung: 'Đang dùng', tat: 'Tắt' }
const KIND = { faq: 'Hỏi đáp', price: 'Giá', service: 'Dịch vụ', project: 'Dự án' }
const SOURCE = { mau: 'dữ liệu mẫu', ai: 'AI soạn', nhan_vien: 'nhân viên', tep: 'tệp' }
const TABS = [{ id: 'muc', label: 'Mục tri thức' }, { id: 'cau-hoi', label: 'Câu hỏi chưa trả lời' }]

/* the four fields of an entry, shared by "new" and "edit" */
const EntryFields = defineComponent({
  props: { form: Object, errors: Object, idPrefix: String, titleLocked: Boolean },
  setup(p) {
    const field = (key, label, input, help) => h('div', { class: 'field' }, [
      h('label', { for: p.idPrefix + '-' + key }, label), input,
      help && h('span', { class: 'small', id: p.idPrefix + '-' + key + '-h' }, help),
      p.errors[key] && h('span', { class: 'field-err', role: 'alert', id: p.idPrefix + '-' + key + '-e' }, p.errors[key])
    ])
    const attrs = (key, extra = {}) => ({
      id: p.idPrefix + '-' + key, class: 'txt', value: p.form[key], 'aria-invalid': p.errors[key] ? 'true' : null,
      'aria-describedby': [extra.help && p.idPrefix + '-' + key + '-h', p.errors[key] && p.idPrefix + '-' + key + '-e'].filter(Boolean).join(' ') || null,
      onInput: e => { p.form[key] = e.target.value }
    })
    return () => h('div', { class: 'kn-fields' }, [
      field('kind', 'Loại', h('select', { ...attrs('kind'), onChange: e => { p.form.kind = e.target.value } },
        Object.entries(KIND).map(([v, t]) => h('option', { value: v, selected: p.form.kind === v }, t)))),
      field('title', 'Tiêu đề', h('input', { ...attrs('title', { help: p.titleLocked }), maxlength: 200, readonly: p.titleLocked }),
        p.titleLocked ? 'Điểm nóng đang liên kết tới tiêu đề này nên không đổi được.' : null),
      field('cum_tu_khop', 'Cụm từ khớp', h('input', { ...attrs('cum_tu_khop', { help: true }), maxlength: 500 }),
        'Cách khách hay hỏi, vd «mất bao lâu thời gian hoàn thành thiết kế». Trợ lý so câu hỏi với tiêu đề và cụm từ này.'),
      field('content', 'Câu trả lời', h('textarea', { ...attrs('content', { help: true }), rows: 5, maxlength: 4000 }),
        (p.form.content || '').length + '/4000')
    ])
  }
})

const route = useRoute()
const router = useRouter()
const tab = computed(() => (route.query.tab === 'cau-hoi' ? 'cau-hoi' : 'muc'))
const tabEls = ref([])
const isApprover = computed(() => hasRole(APPROVERS))

const items = ref([])
const dem = ref({})
const gaps = ref([])
const gapCount = computed(() => gaps.value.length)
const q = ref('')
const filter = ref('')
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const note = ref('')
const editing = ref(null) // 'new' | entry id
const form = reactive({ kind: 'faq', title: '', cum_tu_khop: '', content: '', tu_cau_hoi: [] })
const fieldErr = reactive({})
const delEl = ref(null)
const deleting = ref(null)
let deleteOpener = null

const priceBlocked = e => !isApprover.value && needsPriceApproval(e.kind, e.content)
const when = t => (t ? new Date(t).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : '')

async function load() {
  loading.value = true
  try {
    const r = await listKnowledge({ ...(q.value.trim() ? { q: q.value.trim() } : {}), ...(filter.value ? { trang_thai: filter.value } : {}) })
    items.value = r.items
    dem.value = r.dem
    gaps.value = await knowledgeGaps()
    error.value = ''
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
let timer = null
function reloadSoon() { clearTimeout(timer); timer = setTimeout(load, 250) }
function setFilter(k) { filter.value = k; load() }

const select = id => router.replace({ query: { ...route.query, tab: id === 'muc' ? undefined : id } })
function onTabKey(e) {
  const at = TABS.findIndex(t => t.id === tab.value)
  const to = e.key === 'ArrowRight' ? (at + 1) % TABS.length : e.key === 'ArrowLeft' ? (at + TABS.length - 1) % TABS.length : -1
  if (to < 0) return
  e.preventDefault(); select(TABS[to].id); nextTick(() => tabEls.value[to]?.focus())
}

function fill(src) {
  Object.assign(form, { kind: src.kind || 'faq', title: src.title || '', cum_tu_khop: src.cum_tu_khop || '', content: src.content || '',
    tu_cau_hoi: src.tu_cau_hoi || [] })
  Object.keys(fieldErr).forEach(k => delete fieldErr[k])
}
function startNew(prefill = {}) {
  fill(prefill); editing.value = 'new'; note.value = ''
  nextTick(() => document.getElementById('new-' + (prefill.title ? 'content' : 'title'))?.focus())
}
function toggleEdit(e) {
  if (editing.value === e.id) { closeEditor(); return }
  fill(e); editing.value = e.id; note.value = ''
}
function closeEditor() { editing.value = null }

function showError(err) {
  Object.keys(fieldErr).forEach(k => delete fieldErr[k])
  if (err.status === 409 && /title/.test(String(err.detail))) fieldErr.title = 'Tiêu đề này đã có.'
  else if (err.status === 409) fieldErr.title = err.detail
  else if (Array.isArray(err.detail)) err.detail.forEach(d => { fieldErr[d.loc?.[d.loc.length - 1] || 'content'] = d.msg })
  else error.value = typeof err.detail === 'string' ? err.detail : err.message
}
function validate() {
  Object.keys(fieldErr).forEach(k => delete fieldErr[k])
  for (const [k, label] of [['title', 'Tiêu đề'], ['cum_tu_khop', 'Cụm từ khớp'], ['content', 'Câu trả lời']]) {
    if (!form[k].trim()) fieldErr[k] = label + ' không được để trống.'
  }
  return !Object.keys(fieldErr).length
}

async function act(fn) {
  busy.value = true; error.value = ''
  try { await fn(); return true } catch (e) { showError(e); return false } finally { busy.value = false }
}

async function saveNew(mode) {
  if (!validate()) return
  const ok = await act(async () => {
    const made = await createKnowledge({ kind: form.kind, title: form.title.trim(), cum_tu_khop: form.cum_tu_khop.trim(),
      content: form.content.trim(), trang_thai: mode === 'cho_duyet' ? 'cho_duyet' : 'nhap', tu_cau_hoi: form.tu_cau_hoi })
    if (mode === 'on') await setKnowledgeStatus(made.id, 'dang_dung')
    note.value = mode === 'on' ? `Đã bật «${made.title}», trợ lý dùng từ câu hỏi tiếp theo.`
      : mode === 'cho_duyet' ? `Đã gửi «${made.title}» cho KTS trưởng duyệt.` : `Đã lưu nháp «${made.title}».`
  })
  if (ok) { editing.value = null; await load() }
}

async function saveEdit(e) {
  if (!validate()) return
  const body = {}
  for (const k of ['kind', 'title', 'cum_tu_khop', 'content']) if (form[k].trim() !== (e[k] || '')) body[k] = form[k].trim()
  if (!Object.keys(body).length) { note.value = 'Không có thay đổi.'; return }
  let after = null
  const ok = await act(async () => { after = await updateKnowledge(e.id, body) })
  if (!ok) return
  note.value = after.trang_thai !== e.trang_thai && after.trang_thai === 'cho_duyet'
    ? `Đã lưu. Câu trả lời có giá nên «${after.title}» chuyển sang Chờ duyệt; trợ lý tạm không dùng đến khi KTS trưởng duyệt.`
    : `Đã lưu «${after.title}».`
  await load()
  fill(after)
}

async function move(e, to) {
  const ok = await act(() => setKnowledgeStatus(e.id, to))
  if (!ok) return
  note.value = { dang_dung: `Đã bật «${e.title}».`, cho_duyet: `Đã gửi «${e.title}» cho KTS trưởng duyệt.`,
    tat: `Đã tắt «${e.title}».`, nhap: `Đã đưa «${e.title}» về nháp.` }[to]
  editing.value = null
  await load()
}

function askDelete(e, ev) { deleting.value = e; deleteOpener = ev.currentTarget; nextTick(() => delEl.value.showModal()) }
function onDelClose() { const back = deleteOpener; deleting.value = null; deleteOpener = null; if (back?.isConnected) back.focus() }
async function doDelete() {
  const e = deleting.value
  const ok = await act(() => deleteKnowledge(e.id))
  deleteOpener = null
  delEl.value.close()
  if (ok) { note.value = `Đã xoá «${e.title}».`; editing.value = null; await load() }
}

async function answerGap(g) {
  await select('muc') // the entries panel must be shown before its field can take focus
  startNew({ title: g.cau_hoi.slice(0, 200), cum_tu_khop: g.cau_hoi.slice(0, 500), tu_cau_hoi: g.ids })
}
async function dismiss(g) {
  if (await act(() => dismissGaps(g.ids))) { note.value = `Đã bỏ qua “${g.cau_hoi}”.`; await load() }
}

/* /quan-tri/tri-thuc#soan=<question> (from a conversation, chat-history): answer the matching open group, so its
   questions close when the entry goes live; otherwise a plain new entry from the question */
const words = t => ((t || '').toLowerCase().replace(/đ/g, 'd').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .match(/[a-z0-9]+/g) || []).join(' ')
async function answerFromHash() {
  if (!route.hash.startsWith('#soan=')) return
  let question = ''
  try { question = decodeURIComponent(route.hash.slice(6)).trim() } catch { /* malformed: ignore */ }
  await router.replace({ query: route.query, hash: '' })
  if (!question) return
  const group = gaps.value.find(g => words(g.cau_hoi) === words(question))
  if (group) return answerGap(group)
  await select('muc')
  startNew({ title: question.slice(0, 200), cum_tu_khop: question.slice(0, 500) })
}

onMounted(async () => { await load(); await answerFromHash() })
</script>

<style scoped>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.kn-page { padding-bottom: clamp(48px, 7vw, 96px) }
.kn-tabs { display: flex; gap: 4px; margin: 24px 0 16px; border-bottom: 1px solid var(--line) }
.kn-tab { background: none; border: 0; border-bottom: 2px solid transparent; margin-bottom: -1px; padding: 10px 14px;
          font: inherit; font-size: 15px; color: var(--dim); cursor: pointer }
.kn-tab[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); font-weight: 600 }
.kn-tab:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px }
.kn-note { margin: 0 0 12px; font-size: 14px; color: var(--ink) }
.kn-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center }
.kn-search { flex: 1 1 240px }
.kn-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 }
:deep(.txt) { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 9px 12px; min-height: 40px; width: 100%; max-width: 100%; color-scheme: dark; font: inherit }
:deep(.txt:focus-visible) { border-color: var(--accent); box-shadow: var(--focus-ring) }
:deep(.kn-fields) { display: grid; gap: 12px }
:deep(.kn-fields .field) { display: grid; gap: 4px }
:deep(.kn-fields label) { font-size: 14px; color: var(--ink) }

.kn-list { list-style: none; margin: 0; padding: 0 }
.kn-item { border-top: 1px solid var(--line-soft) }
.kn-row { display: grid; gap: 4px; width: 100%; text-align: left; background: none; border: 0; padding: 12px 4px; cursor: pointer;
          color: var(--ink); font: inherit }
.kn-row:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 6px }
.kn-title { font-weight: 600 }
.kn-badges { display: flex; flex-wrap: wrap; gap: 6px }
.kn-badge { font-size: 12px; border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; color: var(--dim) }
.kn-badge.is-dang_dung { color: var(--success); border-color: currentColor }
.kn-badge.is-cho_duyet { color: var(--warn); border-color: currentColor }
.kn-badge.is-price { color: var(--accent); border-color: currentColor }
.kn-badge.is-sample, .kn-badge.is-ai { color: var(--ink) }
.kn-excerpt { font-size: 14px; color: var(--dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.kn-editor { display: grid; gap: 12px; max-width: 760px; padding: 14px; margin: 0 0 14px; border: 1px solid var(--line);
             border-radius: var(--radius-md) }
.kn-actions { flex-wrap: wrap }
.kn-meta { margin: 0; color: var(--dim) }
.kn-danger { color: var(--danger) }
.kn-gap { display: grid; gap: 6px; padding: 12px 0; border-top: 1px solid var(--line-soft) }
.kn-gap-q { margin: 0; color: var(--ink); overflow-wrap: anywhere }
.kn-gap p.small { margin: 0 }
.kn-terms { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 }
.kn-dialog { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--page); color: var(--ink);
             padding: 20px; width: min(480px, calc(100vw - 32px)) }
.kn-dialog::backdrop { background: rgba(0, 0, 0, 0.55) }
</style>
