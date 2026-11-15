<template>
  <div class="ft">
    <p class="small" style="margin-top:0">
      Khi câu hỏi của khách hoặc câu trả lời nháp chứa một từ khoá đang bật, trợ lý không trả lời mà chuyển cho kiến trúc sư.
      Khách không được biết chủ đề nào bị chặn. So khớp không phân biệt hoa thường, có dấu hay không dấu, và theo nguyên từ.
    </p>

    <form class="ft-try" @submit.prevent="runTry">
      <label for="ft-try">Thử câu</label>
      <div class="ft-try-row">
        <input id="ft-try" v-model="sample" class="txt" maxlength="1000" placeholder="vd: bên công ty khác báo rẻ hơn">
        <button class="btn btn-secondary" :disabled="!sample.trim()">Thử</button>
      </div>
      <p v-if="tried" class="small ft-result" role="status">
        <template v-if="tried.trung">Trúng «{{ tried.trung.ten }}», qua từ khoá «{{ tried.trung.tu_khoa }}».</template>
        <template v-else>Không trúng chủ đề nào đang bật.</template>
      </p>
    </form>

    <div class="ft-bar">
      <h2 class="h-4" style="margin:0">Chủ đề <span class="num">({{ topics.length }})</span></h2>
      <button class="btn btn-primary" type="button" @click="startEdit('new')">+ Chủ đề mới</button>
    </div>
    <p v-if="msg" class="kn-note" role="status">{{ msg }}</p>
    <p v-if="err" class="field-err" role="alert">{{ err }}</p>

    <form v-if="editing === 'new'" class="kn-editor" @submit.prevent="save(null)">
      <h3 class="h-4" style="margin:0">Chủ đề mới</h3>
      <TopicFields :form="form" :errors="fieldErr" prefix="ft-new" />
      <div class="row g10"><button class="btn btn-primary" :disabled="busy">Lưu</button>
        <button class="btn btn-ghost" type="button" @click="editing = null">Huỷ</button></div>
    </form>

    <p v-if="!topics.length && !loading" class="small">Chưa có chủ đề nào.</p>
    <ul class="kn-list">
      <li v-for="t in topics" :key="t.id" class="kn-item ft-item">
        <div class="ft-head">
          <span class="kn-title">{{ t.ten }}</span>
          <label class="ft-switch">
            <input type="checkbox" role="switch" :checked="t.bat" :disabled="busy" @change="toggle(t, $event.target.checked)">
            {{ t.bat ? 'Đang bật' : 'Đang tắt' }}<span class="sr-only"> chủ đề {{ t.ten }}</span>
          </label>
        </div>
        <p class="kn-badges ft-kws"><span class="sr-only">Từ khoá:</span>
          <span v-for="k in t.tu_khoa" :key="k" class="kn-badge">{{ k }}</span></p>
        <p v-if="t.ghi_chu" class="small ft-note">{{ t.ghi_chu }}</p>
        <div class="row g10">
          <button class="btn btn-ghost" type="button" :aria-expanded="String(editing === t.id)" @click="startEdit(t)">Sửa<span class="sr-only"> {{ t.ten }}</span></button>
          <button v-if="isApprover" class="btn btn-ghost kn-danger" type="button" :disabled="busy" @click="remove(t)">Xoá<span class="sr-only"> {{ t.ten }}</span></button>
        </div>
        <form v-if="editing === t.id" class="kn-editor" @submit.prevent="save(t)">
          <TopicFields :form="form" :errors="fieldErr" :prefix="'ft-' + t.id" />
          <div class="row g10"><button class="btn btn-primary" :disabled="busy">Lưu</button>
            <button class="btn btn-ghost" type="button" @click="editing = null">Đóng</button></div>
        </form>
      </li>
    </ul>
  </div>
</template>

<script setup>
/* "Chủ đề cấm" tab of /quan-tri/tri-thuc (seq-3 b15): content staff, lead architect, admin. Only approvers delete;
 * content staff switch a topic off instead. */
import { defineComponent, h, nextTick, onMounted, reactive, ref } from 'vue'
import { createTopic, deleteTopic, listTopics, tryTopics, updateTopic } from '@/api'

defineProps({ isApprover: Boolean })

const TopicFields = defineComponent({
  props: { form: Object, errors: Object, prefix: String },
  setup(p) {
    const field = (key, label, input, help) => h('div', { class: 'field' }, [
      h('label', { for: p.prefix + '-' + key }, label), input,
      help && h('span', { class: 'small', id: p.prefix + '-' + key + '-h' }, help),
      p.errors[key] && h('span', { class: 'field-err', role: 'alert', id: p.prefix + '-' + key + '-e' }, p.errors[key])
    ])
    const attrs = (key, help) => ({
      id: p.prefix + '-' + key, class: 'txt', value: p.form[key], 'aria-invalid': p.errors[key] ? 'true' : null,
      'aria-describedby': [help && p.prefix + '-' + key + '-h', p.errors[key] && p.prefix + '-' + key + '-e'].filter(Boolean).join(' ') || null,
      onInput: e => { p.form[key] = e.target.value }
    })
    return () => h('div', { class: 'kn-fields' }, [
      field('ten', 'Tên chủ đề', h('input', { ...attrs('ten'), maxlength: 80 })),
      field('tu_khoa', 'Từ khoá', h('textarea', { ...attrs('tu_khoa', true), rows: 4 }),
        'Mỗi dòng một từ hoặc cụm từ, 2 đến 60 ký tự, tối đa 30 dòng.'),
      field('ghi_chu', 'Ghi chú nội bộ', h('input', { ...attrs('ghi_chu'), maxlength: 300 }))
    ])
  }
})

const topics = ref([])
const loading = ref(true)
const busy = ref(false)
const msg = ref('')
const err = ref('')
const editing = ref(null)
const form = reactive({ ten: '', tu_khoa: '', ghi_chu: '' })
const fieldErr = reactive({})
const sample = ref('')
const tried = ref(null)

async function load() {
  loading.value = true
  try { topics.value = await listTopics(); err.value = '' } catch (e) { err.value = e.message } finally { loading.value = false }
}

function clearErr() { Object.keys(fieldErr).forEach(k => delete fieldErr[k]) }
function startEdit(t) {
  clearErr(); msg.value = ''
  if (t !== 'new' && editing.value === t.id) { editing.value = null; return }
  Object.assign(form, t === 'new' ? { ten: '', tu_khoa: '', ghi_chu: '' }
    : { ten: t.ten, tu_khoa: t.tu_khoa.join('\n'), ghi_chu: t.ghi_chu || '' })
  editing.value = t === 'new' ? 'new' : t.id
  const prefix = t === 'new' ? 'ft-new' : 'ft-' + t.id
  nextTick(() => document.getElementById(prefix + '-ten')?.focus())
}
const keywords = () => form.tu_khoa.split('\n').map(s => s.trim()).filter(Boolean)

function focusFirstError() {
  const prefix = editing.value === 'new' ? 'ft-new' : 'ft-' + editing.value
  const first = ['ten', 'tu_khoa', 'ghi_chu'].find(k => fieldErr[k])
  if (first) nextTick(() => document.getElementById(prefix + '-' + first)?.focus())
}

async function act(fn) {
  busy.value = true; err.value = ''
  try { return (await fn()) ?? true } catch (e) {
    clearErr()
    if (e.status === 409) fieldErr.ten = 'Đã có chủ đề cùng tên.'
    else if (Array.isArray(e.detail)) e.detail.forEach(d => { fieldErr[d.loc?.[d.loc.length - 1] || 'ten'] = d.msg })
    else err.value = typeof e.detail === 'string' ? e.detail : e.message
    focusFirstError()
    return null
  } finally { busy.value = false }
}

async function save(t) {
  clearErr()
  if (!form.ten.trim()) fieldErr.ten = 'Tên chủ đề không được để trống.'
  if (!keywords().length) fieldErr.tu_khoa = 'Cần ít nhất một từ khoá.'
  if (Object.keys(fieldErr).length) return focusFirstError()
  const body = { ten: form.ten.trim(), tu_khoa: keywords(), ghi_chu: form.ghi_chu.trim() || null }
  const done = await act(() => (t ? updateTopic(t.id, body) : createTopic(body)))
  if (!done) return
  msg.value = `Đã lưu «${done.ten}».`
  editing.value = null
  await load()
}

async function toggle(t, on) {
  const done = await act(() => updateTopic(t.id, { bat: on }))
  if (done) { msg.value = `${on ? 'Đã bật' : 'Đã tắt'} «${t.ten}».`; t.bat = done.bat } else await load()
}

async function remove(t) {
  if (!window.confirm(`Xoá chủ đề «${t.ten}»?`)) return
  if (await act(() => deleteTopic(t.id))) { msg.value = `Đã xoá «${t.ten}».`; await load() }
}

async function runTry() {
  const r = await act(() => tryTopics(sample.value.trim()))
  if (r) tried.value = r
}

onMounted(load)
</script>

<style scoped>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.ft { display: grid; gap: 14px }
.ft-try { display: grid; gap: 6px; max-width: 760px }
.ft-try label { font-size: 14px; color: var(--ink) }
.ft-try-row { display: flex; gap: 10px; flex-wrap: wrap }
.ft-try-row .txt { flex: 1 1 220px; width: auto }
.ft-result { margin: 0; color: var(--ink) }
.ft-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between }
.ft-item { display: grid; gap: 8px; padding: 12px 0 }
.ft-head { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between }
.ft-switch { display: inline-flex; gap: 6px; align-items: center; font-size: 14px; color: var(--dim); cursor: pointer }
.ft-switch input { width: 18px; height: 18px; accent-color: var(--accent) }
.ft-kws, .ft-note { margin: 0; overflow-wrap: anywhere }
.kn-list { list-style: none; margin: 0; padding: 0 }
.kn-item { border-top: 1px solid var(--line-soft) }
.kn-title { font-weight: 600; overflow-wrap: anywhere }
.kn-badges { display: flex; flex-wrap: wrap; gap: 6px }
.kn-badge { font-size: 12px; border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; color: var(--dim) }
.kn-editor { display: grid; gap: 12px; max-width: 760px; padding: 14px; border: 1px solid var(--line); border-radius: var(--radius-md) }
.kn-note { margin: 0; font-size: 14px; color: var(--ink) }
.kn-danger { color: var(--danger) }
.txt { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 9px 12px; min-height: 40px; width: 100%; max-width: 100%; color-scheme: dark; font: inherit }
:deep(.kn-fields) { display: grid; gap: 12px }
:deep(.kn-fields .field) { display: grid; gap: 4px }
:deep(.kn-fields label) { font-size: 14px; color: var(--ink) }
</style>
