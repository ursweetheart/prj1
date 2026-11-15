<template>
  <main class="wrap wrap-wide page-top cv-page">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Hội thoại với trợ lý</h1>
    <p class="lead" style="margin-top:10px">
      Khách đã hỏi gì và trợ lý trả lời ra sao. Lưu ẩn danh 90 ngày; số điện thoại và email trong tin nhắn đã được che.
    </p>

    <div class="cv-bar">
      <div class="row g6" role="group" aria-label="Lọc hội thoại">
        <button v-for="(t, k) in FILTERS" :key="k" type="button" class="chip" :aria-pressed="String(loc === k)"
                @click="loc = k">{{ t }}</button>
      </div>
      <div class="row g6" role="group" aria-label="Khoảng thời gian">
        <button v-for="d in [7, 30, 90]" :key="d" type="button" class="chip" :aria-pressed="String(days === d)"
                @click="days = d">{{ d }} ngày</button>
      </div>
    </div>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!data" class="small" style="margin-top:20px">Đang tải…</p>
    <p v-else-if="!data.items.length" class="small" style="margin-top:20px">Không có hội thoại nào.</p>

    <template v-else>
      <p class="small cv-count num">{{ data.tong }} hội thoại</p>
      <ul class="cv-list">
        <li v-for="c in data.items" :key="c.id" class="cv-item">
          <button type="button" class="cv-toggle" :aria-expanded="String(!!open[c.id])" :aria-controls="'cv-d-' + c.id"
                  @click="toggle(c.id)">
            <span class="cv-first">{{ c.cau_dau || '(trống)' }}</span>
            <span class="cv-meta small">
              <span class="num">{{ when(c.cap_nhat) }}</span>
              <span class="num">{{ c.so_tin_nhan / 2 }} câu hỏi</span>
              <span v-if="c.chua_tra_loi" class="cv-badge is-miss">{{ c.chua_tra_loi }} chưa trả lời được</span>
              <span v-if="c.da_chuyen_nguoi_that" class="cv-badge">Đã chuyển người thật</span>
              <span v-if="c.lead_id" class="cv-badge is-lead">Khách tiềm năng</span>
            </span>
          </button>

          <section v-if="open[c.id]" :id="'cv-d-' + c.id" class="cv-detail" aria-label="Nội dung hội thoại">
            <p v-if="detail[c.id]?.error" class="small" style="color:var(--danger)" role="alert">{{ detail[c.id].error }}</p>
            <p v-else-if="!detail[c.id]?.data" class="small">Đang tải…</p>
            <template v-else>
              <p v-if="facts(detail[c.id].data.rang_buoc).length" class="small cv-facts">
                Khách đã nói: <span v-for="f in facts(detail[c.id].data.rang_buoc)" :key="f" class="cv-fact">{{ f }}</span>
              </p>
              <ol class="cv-thread">
                <li v-for="(m, i) in detail[c.id].data.tin_nhan" :key="i" :class="'is-' + m.vai_tro">
                  <span class="cv-who small">{{ m.vai_tro === 'khach' ? 'Khách' : 'Trợ lý' }}</span>
                  <p class="cv-text">{{ m.noi_dung }}</p>
                  <p v-if="m.vai_tro === 'tro_ly'" class="small cv-src">
                    <span v-if="m.tra_loi_duoc === false" class="cv-badge is-miss">Chưa trả lời được</span>
                    <span v-if="m.diem_cao_nhat !== null" class="num">điểm {{ m.diem_cao_nhat.toFixed(2) }}</span>
                    <span v-if="m.nguon.length">Nguồn: {{ m.nguon.map(s => s.title).join(', ') }}</span>
                    <router-link v-if="m.tra_loi_duoc === false && canWrite && question(detail[c.id].data, i)"
                                 :to="{ path: '/quan-tri/tri-thuc', hash: '#soan=' + encodeURIComponent(question(detail[c.id].data, i)) }">
                      Soạn đáp án →</router-link>
                  </p>
                </li>
              </ol>
              <router-link v-if="c.lead_id && canSeeLeads" class="small" to="/khach-hang">Xem khách tiềm năng #{{ c.lead_id }} →</router-link>
            </template>
          </section>
        </li>
      </ul>
      <button v-if="data.items.length < data.tong" type="button" class="btn btn-secondary" style="margin-top:16px"
              :disabled="more" @click="loadMore">{{ more ? 'Đang tải…' : 'Xem thêm' }}</button>
    </template>
  </main>
</template>

<script setup>
/* Hội thoại với trợ lý (chat-history; seq-3 b18) cho nội dung, kinh doanh, KTS trưởng, admin. Văn bản đã che liên hệ. */
import { computed, reactive, ref, watch } from 'vue'
import { APPROVERS, SALES, getConversation, hasRole, listConversations } from '@/api'

const FILTERS = { tat_ca: 'Tất cả', chua_tra_loi: 'Chưa trả lời được', lead: 'Thành khách tiềm năng' }
const FACT = { project_type: 'Loại công trình', space_type: 'Không gian', area_m2: 'Diện tích', design_style: 'Phong cách' }

const loc = ref('tat_ca')
const days = ref(30)
const data = ref(null)
const error = ref('')
const more = ref(false)
const open = reactive({})
const detail = reactive({})

const canWrite = computed(() => hasRole(['content', ...APPROVERS])) // the knowledge screen's roles
const canSeeLeads = computed(() => hasRole(SALES))
const when = t => new Date(t).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
const facts = rb => Object.entries(rb || {}).filter(([k, v]) => FACT[k] && v !== null)
  .map(([k, v]) => FACT[k] + ': ' + (k === 'area_m2' ? v + ' m²' : String(v).replaceAll('_', ' ')))
// the visitor message an unanswered reply was about
const question = (d, i) => (i > 0 && d.tin_nhan[i - 1].vai_tro === 'khach' ? d.tin_nhan[i - 1].noi_dung : '')

async function load() {
  error.value = ''
  try { data.value = await listConversations({ loc: loc.value, days: days.value }) } catch (e) { error.value = e.message }
}
async function loadMore() {
  more.value = true
  try {
    const r = await listConversations({ loc: loc.value, days: days.value, offset: data.value.items.length })
    data.value = { tong: r.tong, items: [...data.value.items, ...r.items] }
  } catch (e) { error.value = e.message } finally { more.value = false }
}
async function toggle(id) {
  open[id] = !open[id]
  if (!open[id] || detail[id]?.data) return
  detail[id] = { data: null, error: '' }
  try { detail[id].data = await getConversation(id) } catch (e) { detail[id].error = e.message }
}
watch([loc, days], load, { immediate: true })
</script>

<style scoped>
.cv-page { padding-bottom: clamp(28px, 4vw, 56px) }
.cv-bar { display: flex; flex-wrap: wrap; gap: 12px 24px; margin-top: 20px }
.cv-bar .row { flex-wrap: wrap }
.cv-count { margin-top: 16px; color: var(--faint) }
.cv-list { list-style: none; padding: 0; margin: 10px 0 0; display: grid; gap: 10px }
.cv-item { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel); min-width: 0 }
.cv-toggle { all: unset; box-sizing: border-box; width: 100%; cursor: pointer; display: grid; gap: 6px; padding: 12px 14px }
.cv-toggle:focus-visible { outline: 2px solid var(--ink-2); outline-offset: -2px; border-radius: var(--radius-md) }
.cv-first { color: var(--ink); overflow-wrap: anywhere }
.cv-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; color: var(--faint) }
.cv-badge { font-size: 11px; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--line); color: var(--dim); white-space: nowrap }
.cv-badge.is-miss { border-color: var(--danger); color: var(--danger) }
.cv-badge.is-lead { border-color: var(--success); color: var(--success) }
.cv-detail { border-top: 1px solid var(--line-soft); padding: 14px; display: grid; gap: 12px; min-width: 0 }
.cv-facts { margin: 0; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; color: var(--dim) }
.cv-fact { padding: 1px 8px; border-radius: 999px; background: var(--line-soft); color: var(--ink-2) }
.cv-thread { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px }
.cv-thread li { max-width: min(640px, 100%); padding: 10px 12px; border-radius: var(--radius-md); background: var(--line-soft); min-width: 0 }
.cv-thread li.is-khach { justify-self: end; background: color-mix(in oklab, var(--accent) 18%, transparent) }
.cv-who { color: var(--faint) }
.cv-text { margin: 4px 0 0; white-space: pre-line; overflow-wrap: anywhere; color: var(--ink) }
.cv-src { margin: 6px 0 0; display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: center; color: var(--faint) }
</style>
