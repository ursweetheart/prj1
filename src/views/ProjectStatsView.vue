<template>
  <main class="wrap wrap-wide page-top ps-page">
    <p class="eyebrow">Phân tích</p>
    <h1 class="h-2" style="margin-top:10px">Hiệu quả dự án</h1>
    <p class="lead" style="margin-top:10px">
      Lượt xem, lượt lưu và khách tiềm năng của từng dự án đã đăng. Lượt xem và lượt lưu chỉ tính khách đã đồng ý.
    </p>
    <p class="small ps-rule">
      Dự án đăng từ {{ reviewDays }} ngày trở lên được so với các dự án cũng đã đăng ít nhất ngần ấy ngày:
      lượt xem trong 30 ngày gần nhất dưới một nửa trung vị thì là «Cần xem lại».
      <template v-if="data && !data.so_sanh.du_so_sanh">
        Hiện mới có {{ data.so_sanh.du_an_du_tuoi }} dự án đủ tuổi, cần ít nhất 3 để so sánh.
      </template>
      <template v-else-if="data && data.so_sanh.median_views !== null">
        Trung vị hiện tại: <span class="num">{{ fmt(data.so_sanh.median_views) }}</span> lượt xem.
      </template>
    </p>

    <p v-if="data?.co_du_lieu_mo_phong" class="ps-demo" role="note">
      Đang hiển thị cả dữ liệu mô phỏng. Xóa bằng <code>python -m pipeline.demo_activity --remove</code> trước khi dùng thật.
    </p>

    <div class="ps-bar">
      <div class="row g6" role="group" aria-label="Khoảng thời gian">
        <button v-for="d in [30, 90]" :key="d" type="button" class="chip" :aria-pressed="String(days === d)"
                @click="days = d">{{ d }} ngày</button>
      </div>
      <label v-if="canUpload" class="row g10 small"><input v-model="mine" type="checkbox"> Chỉ dự án tôi tải lên</label>
    </div>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!data" class="small" style="margin-top:20px">Đang tải…</p>
    <p v-else-if="!data.projects.length" class="small" style="margin-top:20px">
      {{ mine ? 'Bạn chưa tải lên ảnh nào của một dự án đã đăng.' : 'Chưa có dự án nào có ảnh đã đăng.' }}
    </p>

    <div v-else class="ps-list">
      <div class="ps-head" aria-hidden="true">
        <span>Dự án</span><span>Ảnh</span><span>Ngày đăng</span><span>Lượt xem</span><span>Lưu</span>
        <span>Tỉ lệ lưu</span><span>Khách tiềm năng</span><span>Trạng thái</span>
      </div>
      <article v-for="p in data.projects" :key="p.folder" class="ps-item" :class="{ 'is-open': open[p.folder] }">
        <div class="ps-row">
          <h2 class="ps-name">
            <button type="button" class="ps-toggle" :aria-expanded="String(!!open[p.folder])"
                    :aria-controls="'ps-d-' + p.folder" @click="toggle(p.folder)">
              <span class="ps-caret" aria-hidden="true">▸</span>{{ p.ten || nameOf(p.folder) }}
            </button>
          </h2>
          <p class="ps-cell"><span class="ps-k">Ảnh</span><span class="num">{{ p.so_anh }}</span></p>
          <p class="ps-cell"><span class="ps-k">Ngày đăng</span>
            <span class="num" :title="p.ngay_dang_uoc_tinh ? 'Ước tính từ ngày tải lên' : null">{{ dateText(p) }}</span></p>
          <p class="ps-cell"><span class="ps-k">Lượt xem</span><span class="num">{{ fmt(p.luot_xem) }}</span></p>
          <p class="ps-cell"><span class="ps-k">Lưu</span><span class="num">{{ fmt(p.luot_luu) }}</span></p>
          <p class="ps-cell"><span class="ps-k">Tỉ lệ lưu</span><span class="num">{{ p.ti_le_luu === null ? '–' : p.ti_le_luu + '%' }}</span></p>
          <p class="ps-cell"><span class="ps-k">Khách tiềm năng</span><span class="num">{{ p.khach_tiem_nang }}</span></p>
          <p class="ps-cell ps-status"><span class="ps-k">Trạng thái</span>
            <span class="ps-badge" :class="'is-' + p.trang_thai">{{ statusText(p) }}</span></p>
        </div>

        <section v-if="open[p.folder]" :id="'ps-d-' + p.folder" class="ps-detail" :aria-label="'Chi tiết ' + (p.ten || nameOf(p.folder))">
          <p v-if="detail[p.folder]?.error" class="small" style="color:var(--danger)" role="alert">{{ detail[p.folder].error }}</p>
          <p v-else-if="!detail[p.folder]?.data" class="small">Đang tải…</p>
          <template v-else>
            <h3 class="ps-h">Ảnh theo lượt xem <span class="ps-note">{{ days }} ngày</span></h3>
            <ol class="ps-photos">
              <li v-for="ph in detail[p.folder].data.photos" :key="ph.id" :class="{ 'is-unseen': ph.chua_ai_xem }">
                <img :src="imageUrl(ph.relative_path)" alt="" loading="lazy">
                <span class="ps-pn num">{{ ph.luot_xem }} xem · {{ ph.luot_luu }} lưu</span>
                <span v-if="ph.chua_ai_xem" class="ps-unseen">chưa ai xem</span>
                <span v-if="flagged(p.folder).has(ph.id)" class="ps-flag">cần sửa</span>
              </li>
            </ol>

            <h3 class="ps-h">Gợi ý</h3>
            <ul v-if="detail[p.folder].data.goi_y.length" class="ps-tips">
              <li v-for="g in detail[p.folder].data.goi_y" :key="g.ma">
                <span>{{ g.text }}</span>
                <router-link v-if="canFix" :to="g.link" class="ps-fix">Sửa ở trang Duyệt</router-link>
              </li>
            </ul>
            <p v-else class="small">Không có gì cần sửa: đủ nhãn, phong cách rõ, chú thích đầy đủ và ảnh nào cũng có người xem.</p>
          </template>
        </section>
      </article>
    </div>
  </main>
</template>

<script setup>
/* Hiệu quả dự án (BFD 5.4; act-1 "theo dõi hiệu quả sau 30 ngày") cho KTS, KTS trưởng, admin và kinh doanh.
   Chỉ số đếm, không có phiên hay liên hệ của khách. */
import { computed, reactive, ref, watch } from 'vue'
import { EDITORS, STAFF, getProjectDetail, getProjectStats, hasRole, imageUrl } from '@/api'
import { projectBySlug } from '@/data/projects'

const STATUS = { can_xem_lai: 'Cần xem lại', on: 'Ổn' }

const days = ref(30)
const mine = ref(false)
const data = ref(null)
const error = ref('')
const open = reactive({})
const detail = reactive({})

const canUpload = computed(() => hasRole(STAFF))
const canFix = computed(() => hasRole(EDITORS))
const reviewDays = computed(() => data.value?.so_sanh.so_ngay_danh_gia ?? 30)

const fmt = n => Number(n || 0).toLocaleString('vi-VN')
const nameOf = folder => projectBySlug(folder.replace(/_/g, '-'))?.name || folder.replace(/_/g, ' ')
const statusText = p => p.trang_thai === 'dang_theo_doi' ? `Đang theo dõi · còn ${p.con_ngay} ngày` : STATUS[p.trang_thai]
function dateText(p) {
  if (!p.ngay_dang) return '–'
  const d = new Date(p.ngay_dang)
  return (p.ngay_dang_uoc_tinh ? '≈ ' : '') + d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
const flagged = folder => new Set((detail[folder]?.data?.goi_y || []).filter(g => g.ma !== 'anh_chua_ai_xem').flatMap(g => g.anh))

async function loadDetail(folder) {
  detail[folder] = { data: null, error: '' }
  try { detail[folder].data = await getProjectDetail(folder, days.value) } catch (e) { detail[folder].error = e.message }
}

function toggle(folder) {
  open[folder] = !open[folder]
  if (open[folder]) loadDetail(folder)
}

async function load() {
  error.value = ''
  try { data.value = await getProjectStats(days.value, mine.value) } catch (e) { error.value = e.message }
  Object.keys(open).filter(f => open[f]).forEach(loadDetail) // the period changes the photo counts
}
watch([days, mine], load, { immediate: true })
</script>

<style scoped>
.ps-page { padding-bottom: clamp(28px, 4vw, 56px) }
.ps-rule { margin-top: 10px; max-width: 70ch; color: var(--dim) }
.ps-demo { margin: 16px 0 0; padding: 12px 14px; border: 1px solid var(--accent); border-radius: var(--radius-md);
           color: var(--ink); font-size: 14px; background: color-mix(in oklab, var(--accent) 12%, transparent) }
.ps-demo code { font-size: 13px; overflow-wrap: anywhere }
.ps-bar { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: center; margin-top: 20px }

.ps-list { margin-top: 20px; display: grid; gap: 10px }
.ps-head { display: none }
.ps-item { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel); min-width: 0 }
.ps-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 16px; padding: 12px 14px }
.ps-name { grid-column: 1 / -1; margin: 0; font-size: 15px; font-weight: 500 }
.ps-toggle { all: unset; cursor: pointer; display: flex; gap: 8px; align-items: baseline; color: var(--ink);
             overflow-wrap: anywhere; min-height: 24px }
.ps-toggle:focus-visible { outline: 2px solid var(--ink-2); outline-offset: 3px; border-radius: 2px }
.ps-caret { display: inline-block; transition: transform .15s; color: var(--dim) }
.is-open .ps-caret { transform: rotate(90deg) }
.ps-cell { margin: 0; display: flex; justify-content: space-between; gap: 8px; font-size: 14px; color: var(--ink-2); min-width: 0 }
.ps-k { color: var(--faint); font-size: 12px }
.ps-status { grid-column: 1 / -1 }
.ps-badge { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--dim); white-space: nowrap }
.ps-badge.is-can_xem_lai { border-color: var(--danger); color: var(--danger) }
.ps-badge.is-on { border-color: var(--success); color: var(--success) }

@media (min-width: 760px) {
  .ps-head, .ps-row { display: grid; grid-template-columns: minmax(0, 2.4fr) .6fr 1.1fr .9fr .7fr .9fr 1.1fr 1.6fr; gap: 12px;
                      align-items: center }
  .ps-head { padding: 0 14px; font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--faint) }
  .ps-name, .ps-status { grid-column: auto }
  .ps-cell { display: block }
  .ps-k { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
}

.ps-detail { border-top: 1px solid var(--line-soft); padding: 14px; min-width: 0 }
.ps-h { margin: 0 0 10px; font-size: 14px; font-weight: 500; color: var(--ink) }
.ps-h:not(:first-child) { margin-top: 18px }
.ps-note { font-size: 12px; font-weight: 400; color: var(--faint); margin-left: 6px }
.ps-photos { list-style: none; margin: 0; padding: 0 0 6px; display: flex; gap: 10px; overflow-x: auto; overscroll-behavior-x: contain }
.ps-photos li { flex: 0 0 140px; display: grid; gap: 4px; align-content: start; font-size: 12px }
.ps-photos img { width: 140px; aspect-ratio: 4 / 3; object-fit: cover; border-radius: var(--radius-sm); display: block }
.ps-photos .is-unseen img { opacity: .55 }
.ps-pn { color: var(--ink-2) }
.ps-unseen, .ps-flag { justify-self: start; font-size: 11px; padding: 1px 6px; border-radius: 999px; border: 1px solid var(--line); color: var(--dim) }
.ps-flag { border-color: var(--accent); color: var(--ink) }
.ps-tips { margin: 0; padding-left: 18px; display: grid; gap: 8px; font-size: 14px; color: var(--ink-2) }
.ps-tips li span { margin-right: 8px }
.ps-fix { white-space: nowrap }
</style>
