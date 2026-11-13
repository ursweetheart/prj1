<template>
  <main class="wrap wrap-wide tr" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Phân tích</p>
    <h1 class="h-2" style="margin-top:10px">Xu hướng quan tâm</h1>
    <p class="lead" style="margin-top:10px">
      Điểm quan tâm theo từng giá trị phân loại: lượt xem × 1, lượt lưu × 3, ảnh gửi trong bộ sưu tập × 5, chỉ từ khách
      đã đồng ý. Xu hướng so 7 ngày gần nhất với trung bình 4 tuần trước đó.
    </p>

    <p v-if="data?.co_du_lieu_mo_phong" class="tr-demo" role="note">
      Đang hiển thị cả dữ liệu mô phỏng. Xóa bằng <code>python -m pipeline.demo_activity --remove</code> trước khi dùng thật.
    </p>

    <div class="row g6 tr-period" role="group" aria-label="Khoảng thời gian">
      <button v-for="d in [7, 30, 90]" :key="d" type="button" class="chip" :aria-pressed="String(days === d)"
              @click="days = d">{{ d }} ngày</button>
    </div>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!data" class="small" style="margin-top:20px">Đang tải…</p>

    <template v-else>
      <!-- totals -->
      <section class="tr-tiles" aria-label="Tổng quan">
        <div class="tr-tile"><p class="tr-k">Lượt xem</p><p class="tr-v num">{{ fmt(data.tong.luot_xem) }}</p>
          <p class="tr-s">{{ data.tong.ti_le_dong_y }}% có đồng ý</p></div>
        <div class="tr-tile"><p class="tr-k">Lượt lưu</p><p class="tr-v num">{{ fmt(data.tong.luot_luu) }}</p></div>
        <div class="tr-tile"><p class="tr-k">Bộ sưu tập đã gửi</p><p class="tr-v num">{{ fmt(data.tong.brief) }}</p></div>
        <div class="tr-tile"><p class="tr-k">Khách tiềm năng</p><p class="tr-v num">{{ fmt(totalLeads) }}</p>
          <p class="tr-s">{{ SOURCES.map(s => s.t + ' ' + data.tong.lead[s.v]).join(' · ') }}</p></div>
      </section>

      <!-- trend alerts -->
      <section class="tr-card" aria-labelledby="tr-alerts">
        <h2 id="tr-alerts" class="tr-h">Cảnh báo xu hướng <span class="tr-note">7 ngày qua so với 4 tuần trước</span></h2>
        <ul v-if="data.canh_bao.length" class="tr-alerts">
          <li v-for="a in data.canh_bao" :key="a.chieu + a.ma" :class="'is-' + a.xu_huong">
            <span class="tr-arrow" aria-hidden="true">{{ ARROW[a.xu_huong] }}</span>
            <span>{{ a.chieu }} · <strong>{{ a.ten }}</strong></span>
            <span class="num tr-change">{{ trendText(a) }}</span>
          </li>
        </ul>
        <p v-else class="small">Chưa có giá trị nào tăng hay giảm rõ rệt (cần ít nhất 5 tín hiệu trong tuần).</p>
      </section>

      <!-- ranking per dimension -->
      <section class="tr-dims" aria-label="Điểm quan tâm theo chiều phân loại">
        <article v-for="d in data.chieu" :key="d.ma" class="tr-card" :aria-labelledby="'dim-' + d.ma">
          <h2 :id="'dim-' + d.ma" class="tr-h">{{ d.ten }}</h2>
          <ol v-if="d.gia_tri.length" class="tr-rank">
            <li v-for="v in d.gia_tri" :key="v.ma">
              <div class="tr-row">
                <span class="tr-name">{{ v.ten }}</span>
                <span class="num tr-pct">{{ v.ti_le }}%</span>
                <span v-if="v.xu_huong || v.thay_doi !== null" class="tr-trend" :class="'is-' + (v.xu_huong || 'flat')"
                      :title="trendText(v)">
                  <span aria-hidden="true">{{ ARROW[v.xu_huong] || '' }}</span>
                  <span class="num">{{ trendShort(v) }}</span>
                </span>
              </div>
              <div class="tr-bar" aria-hidden="true"><span :style="{ width: v.ti_le + '%' }"></span></div>
              <p class="tr-counts num">{{ v.xem }} xem · {{ v.luu }} lưu · {{ v.brief }} ảnh gửi · {{ v.diem }} điểm</p>
            </li>
          </ol>
          <p v-else class="small">Chưa có hoạt động trong {{ days }} ngày.</p>
        </article>
      </section>

      <!-- leads per week -->
      <section class="tr-card" aria-labelledby="tr-leads">
        <h2 id="tr-leads" class="tr-h">Khách tiềm năng theo tuần <span class="tr-note">8 tuần gần nhất</span></h2>
        <ul class="tr-legend" aria-label="Chú thích">
          <li v-for="s in SOURCES" :key="s.v"><span class="tr-sw" :class="'src-' + s.v" aria-hidden="true"></span>{{ s.t }}</li>
        </ul>
        <div class="tr-weeks">
          <div v-for="w in data.lead_theo_tuan" :key="w.tuan_bat_dau" class="tr-week"
               :aria-label="'Tuần ' + weekLabel(w.tuan_bat_dau) + ': ' + SOURCES.map(s => s.t + ' ' + w[s.v]).join(', ')">
            <div class="tr-stack">
              <span v-for="s in SOURCES" :key="s.v" :class="'src-' + s.v"
                    :style="{ height: (w[s.v] / maxWeek * 100) + '%' }"></span>
            </div>
            <span class="tr-wl num">{{ weekLabel(w.tuan_bat_dau) }}</span>
            <span class="tr-wn num">{{ SOURCES.reduce((n, s) => n + w[s.v], 0) }}</span>
          </div>
        </div>
      </section>

      <!-- top spaces -->
      <section class="tr-card" aria-labelledby="tr-top">
        <h2 id="tr-top" class="tr-h">Không gian được xem nhiều <span class="tr-note">{{ days }} ngày</span></h2>
        <ol v-if="data.khong_gian_xem_nhieu.length" class="tr-top">
          <li v-for="s in data.khong_gian_xem_nhieu" :key="s.id">
            <router-link :to="'/khong-gian/' + s.id">
              <img :src="imageUrl(s.relative_path)" alt="" loading="lazy">
              <span>{{ spaceLabel(s.space_type) }}<br><span class="num tr-s">{{ s.luot_xem }} lượt xem</span></span>
            </router-link>
          </li>
        </ol>
        <p v-else class="small">Chưa có lượt xem trong {{ days }} ngày.</p>
      </section>
    </template>
  </main>
</template>

<script setup>
/* Bảng điều khiển xu hướng (UC22; act-3, seq-18) cho TP Kinh doanh, KTS trưởng, admin. Chỉ số tổng hợp, không có dữ liệu cá nhân. */
import { computed, ref, watch } from 'vue'
import { getOverview, imageUrl, spaceLabel } from '@/api'

const SOURCES = [{ v: 'form', t: 'Form' }, { v: 'chat', t: 'Chat' }, { v: 'brief', t: 'Bộ sưu tập' }, { v: 'estimate', t: 'Ước tính' }]
const ARROW = { dang_tang: '↑', moi_noi: '✦', dang_giam: '↓' }
const LABEL = { dang_tang: 'đang tăng', moi_noi: 'mới nổi', dang_giam: 'đang giảm' }

const days = ref(30)
const data = ref(null)
const error = ref('')

const fmt = n => Number(n || 0).toLocaleString('vi-VN')
const totalLeads = computed(() => SOURCES.reduce((n, s) => n + (data.value?.tong.lead[s.v] || 0), 0))
const maxWeek = computed(() => Math.max(1, ...(data.value?.lead_theo_tuan || []).map(w => SOURCES.reduce((n, s) => n + w[s.v], 0))))
const sign = n => (n > 0 ? '+' : '') + n + '%'
const trendText = v => [LABEL[v.xu_huong], v.thay_doi !== null && v.thay_doi !== undefined ? sign(v.thay_doi) : null].filter(Boolean).join(' ')
const trendShort = v => (v.xu_huong === 'moi_noi' ? 'mới' : v.thay_doi !== null ? sign(v.thay_doi) : '')
const weekLabel = iso => { const [, m, d] = iso.split('-'); return d + '/' + m }

async function load() {
  error.value = ''
  try { data.value = await getOverview(days.value) } catch (e) { error.value = e.message }
}
watch(days, load, { immediate: true })
</script>

<style scoped>
.tr-demo { margin: 16px 0 0; padding: 12px 14px; border: 1px solid var(--accent); border-radius: var(--radius-md);
           color: var(--ink); font-size: 14px; background: color-mix(in oklab, var(--accent) 12%, transparent) }
.tr-demo code { font-size: 13px; overflow-wrap: anywhere }
.tr-period { margin-top: 20px; flex-wrap: wrap }
.tr-tiles { display: grid; gap: 14px; margin-top: 24px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)) }
.tr-tile, .tr-card { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel); padding: 16px 18px; min-width: 0 }
.tr-k { margin: 0; font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--faint) }
.tr-v { margin: 6px 0 0; font-family: var(--font-display); font-size: clamp(26px, 3vw, 34px); color: var(--ink) }
.tr-s { margin: 4px 0 0; font-size: 12px; color: var(--dim) }
.tr-card { margin-top: 16px }
.tr-h { margin: 0 0 12px; font-size: 16px; font-weight: 500; color: var(--ink) }
.tr-note { font-size: 12px; font-weight: 400; color: var(--faint); margin-left: 6px }
.tr-alerts { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px }
.tr-alerts li { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; font-size: 14px; color: var(--ink-2) }
.tr-arrow { width: 1.2em; text-align: center; font-weight: 600 }
.is-dang_tang .tr-arrow, .tr-trend.is-dang_tang { color: var(--success) }
.is-moi_noi .tr-arrow, .tr-trend.is-moi_noi { color: var(--accent) }
.is-dang_giam .tr-arrow, .tr-trend.is-dang_giam { color: var(--danger) }
.tr-change { margin-left: auto; color: var(--dim) }
.tr-dims { display: grid; gap: 16px; margin-top: 0; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)) }
.tr-dims .tr-card { margin-top: 16px }
.tr-rank { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px }
.tr-row { display: flex; align-items: baseline; gap: 8px }
.tr-name { flex: 1; min-width: 0; color: var(--ink); font-size: 14px; overflow-wrap: anywhere }
.tr-pct { color: var(--ink-2); font-size: 14px }
.tr-trend { font-size: 12px; color: var(--dim); white-space: nowrap }
.tr-bar { height: 6px; border-radius: 3px; background: var(--line-soft); margin-top: 6px; overflow: hidden }
.tr-bar span { display: block; height: 100%; background: var(--accent); border-radius: 3px }
.tr-counts { margin: 4px 0 0; font-size: 11px; color: var(--faint) }
.tr-legend { list-style: none; padding: 0; margin: 0 0 12px; display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: var(--dim) }
.tr-sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px }
.src-form { background: var(--accent) }
.src-chat { background: var(--ink-2) }
.src-brief { background: var(--success) }
.src-estimate { background: var(--dim) }
.tr-weeks { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 6px; align-items: end }
.tr-week { display: grid; gap: 4px; justify-items: center; min-width: 0 }
.tr-stack { height: 120px; width: min(100%, 36px); display: flex; flex-direction: column-reverse; background: var(--line-soft); border-radius: 3px; overflow: hidden }
.tr-stack span { display: block; width: 100% }
.tr-wl { font-size: 11px; color: var(--faint) }
.tr-wn { font-size: 12px; color: var(--ink-2) }
.tr-top { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 160px), 1fr)) }
.tr-top a { display: grid; gap: 6px; color: var(--ink); text-decoration: none; font-size: 13px }
.tr-top img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: var(--radius-sm); display: block }
.tr-top a:focus-visible { outline: 2px solid var(--ink-2); outline-offset: 3px }
</style>
