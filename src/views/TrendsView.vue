<template>
  <main class="wrap wrap-wide page-top tr" style="padding-bottom:clamp(28px,4vw,56px)">
    <p class="eyebrow">Phân tích</p>
    <h1 class="h-2" style="margin-top:10px">Xu hướng quan tâm</h1>
    <p class="lead" style="margin-top:10px">
      Điểm quan tâm theo từng giá trị phân loại: lượt xem × 1, lượt lưu × 3, ảnh gửi trong bộ sưu tập × 5, chỉ từ khách
      đã đồng ý. Xu hướng so 7 ngày gần nhất với trung bình 4 tuần trước đó.
      Kết quả của từng dự án: <router-link to="/quan-tri/hieu-qua">Hiệu quả dự án</router-link>.
    </p>

    <p v-if="data?.co_du_lieu_mo_phong" class="tr-demo" role="note">
      Đang hiển thị cả dữ liệu mô phỏng. Xóa bằng <code>python -m pipeline.demo_activity --remove</code> trước khi dùng thật.
    </p>

    <p v-if="data" class="small tr-fresh" role="status">{{ data.den_ngay
      ? `Số liệu đến hết ngày ${dateVi(data.den_ngay)} (tổng hợp hằng đêm, từ 1:00).`
      : 'Chưa có số liệu tổng hợp: tiến trình hằng đêm chưa chạy.' }}</p>

    <div class="tr-bar">
      <div class="row g6" role="group" aria-label="Khoảng thời gian">
        <button v-for="d in [7, 30, 90]" :key="d" type="button" class="chip" :aria-pressed="String(days === d)"
                @click="days = d">{{ d }} ngày</button>
      </div>
      <label v-if="optIn !== null" class="row g10 small">
        <input type="checkbox" :checked="optIn" :disabled="optBusy" @change="saveOptIn($event.target.checked)">
        Nhận báo cáo tuần qua email (thứ Hai, 8:00)
      </label>
      <span v-if="optMsg" class="small" role="status">{{ optMsg }}</span>
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
            <span class="num tr-change">{{ a.xu_huong === 'nhom_moi' ? `nhóm thị hiếu mới · ${a.ty_le}% phiên` : trendText(a) }}</span>
            <HomeSettingSelect v-if="home && a.chieu_ma" :value="a.chieu_ma + ':' + a.ma" :name="a.ten" :mode="homeMode(a.chieu_ma, a.ma)"
                               @change="setHome" />
          </li>
        </ul>
        <p v-else class="small">Chưa có giá trị nào tăng hay giảm rõ rệt (cần ít nhất 5 tín hiệu trong tuần).</p>
      </section>

      <!-- act-3: taste groups from the nightly clustering -->
      <section class="tr-card" aria-labelledby="tr-groups">
        <h2 id="tr-groups" class="tr-h">Nhóm thị hiếu <span class="tr-note">phiên 30 ngày, gom theo thuộc tính đã xem</span></h2>
        <p v-if="!data.nhom_thi_hieu" class="small">Chưa có lần phân nhóm nào.</p>
        <p v-else-if="!data.nhom_thi_hieu.du_du_lieu" class="small">
          Chưa đủ dữ liệu để phân nhóm ({{ data.nhom_thi_hieu.so_phien }} phiên đủ điều kiện, cần ít nhất 10).</p>
        <ul v-else class="tr-groups">
          <li v-for="(g, i) in data.nhom_thi_hieu.nhom" :key="i">
            <span class="num tr-gshare">{{ g.ty_le }}%</span>
            <span>{{ g.gia_tri.map(v => v.ten).join(' · ') }} <span class="small">({{ g.so_phien }} phiên)</span></span>
            <span v-if="g.moi" class="tr-new">mới</span>
          </li>
        </ul>
      </section>

      <!-- act-3: what the homepage shows now (leadership adjusts it with the selects beside each value) -->
      <section v-if="home" class="tr-card" aria-labelledby="tr-home">
        <h2 id="tr-home" class="tr-h">Gợi ý trên trang chủ <span class="tr-note">mục «Đang được quan tâm»</span></h2>
        <p class="small" style="margin:0 0 10px">Chọn «Ưu tiên» hoặc «Ẩn» bên cạnh một giá trị trong cảnh báo hoặc bảng xếp hạng;
          «Tự động» để theo xu hướng.</p>
        <ul v-if="home.cai_dat.length" class="bh-list">
          <li v-for="s in home.cai_dat" :key="s.gia_tri">{{ s.chieu }} · <strong>{{ s.ten }}</strong>:
            {{ s.che_do === 'uu_tien' ? 'ưu tiên' : 'ẩn' }} <span class="small">({{ s.boi }})</span></li>
        </ul>
        <ol v-if="home.xem_truoc.length" class="tr-preview">
          <li v-for="s in home.xem_truoc" :key="s.id">
            <router-link :to="'/khong-gian/' + s.id"><img :src="imageUrl(s.relative_path)" :alt="s.alt_text || s.nhan" loading="lazy"></router-link>
            <span class="small">{{ s.nhan }}</span>
          </li>
        </ol>
        <p v-else class="small">Trang chủ chưa có gì để gợi ý.</p>
        <p v-if="homeMsg" class="small" role="status">{{ homeMsg }}</p>
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
                <HomeSettingSelect v-if="home" :value="d.ma + ':' + v.ma" :name="v.ten" :mode="homeMode(d.ma, v.ma)" @change="setHome" />
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

      <WeeklyReportPanel v-if="isApprover" />

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

      <!-- behaviour on the site (behaviour-events) -->
      <section v-if="bh" class="tr-card" aria-labelledby="tr-bh">
        <h2 id="tr-bh" class="tr-h">Hành vi trên trang <span class="tr-note">{{ days }} ngày, khách đã đồng ý</span></h2>
        <div class="bh-grid">
          <div class="bh-block">
            <h3 class="bh-h">Trang được xem nhiều</h3>
            <table v-if="bh.trang.length" class="bh-table">
              <thead><tr><th scope="col">Trang</th><th scope="col">Lượt xem</th><th scope="col">Thời gian TB</th><th scope="col">Cuộn TB</th></tr></thead>
              <tbody>
                <tr v-for="p in bh.trang" :key="p.trang">
                  <td data-k="Trang"><code>{{ p.trang }}</code></td>
                  <td data-k="Lượt xem" class="num">{{ p.luot_xem }}</td>
                  <td data-k="Thời gian TB" class="num">{{ p.giay_tb === null ? '–' : p.giay_tb + ' giây' }}</td>
                  <td data-k="Cuộn TB" class="num">{{ p.cuon_tb === null ? '–' : p.cuon_tb + '%' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="small">Chưa có lượt xem trang.</p>
            <p class="small bh-anon num">Không đồng ý (chỉ đếm): {{ bh.an_danh.xem_trang + bh.an_danh.xem_du_an }} lượt xem trang</p>
          </div>
          <div class="bh-block">
            <h3 class="bh-h">Dự án được xem nhiều</h3>
            <ol v-if="bh.du_an.length" class="bh-list">
              <li v-for="d in bh.du_an" :key="d.du_an"><router-link :to="'/du-an/' + d.du_an">{{ d.du_an }}</router-link>
                <span class="num">{{ d.luot_xem }} lượt · {{ d.giay_tb ?? '–' }} giây</span></li>
            </ol>
            <p v-else class="small">Chưa có.</p>
          </div>
          <div class="bh-block">
            <h3 class="bh-h">Nút kêu gọi (CTA)</h3>
            <ul v-if="bh.cta.length" class="bh-list">
              <li v-for="c in bh.cta" :key="c.dich"><code>{{ c.dich }}</code> <span class="num">{{ c.so_lan }} lần</span>
                <span class="small bh-from">từ {{ c.tu_trang.slice(0, 3).map(t => t.trang + ' (' + t.so_lan + ')').join(', ') }}</span></li>
            </ul>
            <p v-else class="small">Chưa có.</p>
            <p class="small bh-anon num">Không đồng ý: {{ bh.an_danh.bam_CTA }}</p>
          </div>
          <div class="bh-block">
            <h3 class="bh-h">Form, trò chuyện, chia sẻ</h3>
            <ul class="bh-list">
              <li v-for="(n, k) in bh.form" :key="k">Gửi form {{ FORM_VI[k] || k }} <span class="num">{{ n }}</span></li>
              <li>Tin nhắn với trợ lý <span class="num">{{ bh.dong_y.nhan_chatbot }}</span></li>
              <li>Chia sẻ bộ sưu tập <span class="num">{{ bh.dong_y.chia_se }}</span></li>
            </ul>
            <p class="small bh-anon num">Không đồng ý: {{ bh.an_danh.gui_form }} form · {{ bh.an_danh.nhan_chatbot }} tin nhắn · {{ bh.an_danh.chia_se }} chia sẻ</p>
          </div>
          <div class="bh-block">
            <h3 class="bh-h">Tìm kiếm và gợi ý tương tự</h3>
            <ul class="bh-list">
              <li>Tìm bằng mô tả <span class="num">{{ bh.tim_kiem.mo_ta || 0 }}</span></li>
              <li>Tìm bằng ảnh <span class="num">{{ bh.tim_kiem.anh || 0 }}</span></li>
              <li>Gợi ý tương tự đã hiện <span class="num">{{ bh.goi_y.hien }}</span>, được mở <span class="num">{{ bh.goi_y.chon }}</span>
                <span v-if="bh.goi_y.ty_le !== null" class="num">({{ bh.goi_y.ty_le }}%)</span></li>
            </ul>
            <p class="small bh-anon num">Không đồng ý: {{ bh.an_danh.tim_kiem }} lượt tìm · {{ bh.an_danh.xem_goi_y_tuong_tu }} lần hiện gợi ý</p>
          </div>
          <div class="bh-block">
            <h3 class="bh-h">Bộ lọc được dùng</h3>
            <ol v-if="bh.bo_loc.length" class="bh-list">
              <li v-for="f in bh.bo_loc" :key="f.gia_tri">{{ f.gia_tri.split(':')[1].replaceAll('_', ' ') }}
                <span class="small">{{ f.gia_tri.split(':')[0].replaceAll('_', ' ') }}</span> <span class="num">{{ f.so_lan }}</span></li>
            </ol>
            <p v-else class="small">Chưa có.</p>
          </div>
          <div class="bh-block">
            <h3 class="bh-h">Tương tác với ảnh</h3>
            <ul class="bh-list">
              <li>Phóng to ảnh dự án <span class="num">{{ bh.dong_y.phong_to_anh }}</span></li>
              <li>Chuyển ảnh <span class="num">{{ bh.dong_y.chuyen_anh }}</span></li>
              <li>Mở điểm món đồ <span class="num">{{ bh.dong_y.bam_hotspot }}</span></li>
            </ul>
            <p class="small bh-anon num">Không đồng ý: {{ bh.an_danh.phong_to_anh }} phóng to · {{ bh.an_danh.chuyen_anh }} chuyển ảnh · {{ bh.an_danh.bam_hotspot }} điểm món đồ</p>
            <ol v-if="bh.hotspot?.length" class="bh-list" aria-label="Điểm món đồ được mở nhiều">
              <li v-for="x in bh.hotspot" :key="x.doi_tuong">
                <router-link :to="'/khong-gian/' + spotOf(x.doi_tuong).id">ảnh #{{ spotOf(x.doi_tuong).id }}</router-link>
                · {{ spotOf(x.doi_tuong).what }} <span class="num">{{ x.so_lan }}</span></li>
            </ol>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup>
/* Bảng điều khiển xu hướng (UC22; act-3, seq-18) cho TP Kinh doanh, KTS trưởng, admin. Chỉ số tổng hợp, không có dữ liệu cá nhân. */
import { computed, ref, watch } from 'vue'
import { APPROVERS, getBehaviour, getHomeSettings, getOverview, getWeeklyOptIn, hasRole, imageUrl, setHomeSetting, setWeeklyOptIn, spaceLabel } from '@/api'
import HomeSettingSelect from '@/components/HomeSettingSelect.vue'
import WeeklyReportPanel from '@/components/WeeklyReportPanel.vue'

const SOURCES = [{ v: 'form', t: 'Form' }, { v: 'chat', t: 'Chat' }, { v: 'brief', t: 'Bộ sưu tập' }, { v: 'estimate', t: 'Ước tính' }]
const ARROW = { dang_tang: '↑', moi_noi: '✦', nhom_moi: '◆', dang_giam: '↓' }
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

const bh = ref(null) // behaviour-events: pages, CTAs, forms, chat, shares, filters
const FORM_VI = { lien_he: 'liên hệ', brief: 'bộ sưu tập', uoc_tinh: 'ước tính' }
// bam_hotspot object: "<space id>/mon_do_<item id>" or "<space id>/<label slug>"
const spotOf = o => {
  const [id, rest = ''] = o.split('/')
  return { id, what: rest.startsWith('mon_do_') ? 'món đồ #' + rest.slice(7) : rest.replaceAll('_', ' ') }
}
async function load() {
  error.value = ''
  try { data.value = await getOverview(days.value) } catch (e) { error.value = e.message }
  bh.value = await getBehaviour(days.value).catch(() => null) // the dashboard works without it
  home.value = await getHomeSettings().catch(() => null)
}
const dateVi = iso => { const [y, m, d] = iso.split('-'); return `${d}/${m}/${y}` }

/* act-3 "Điều chỉnh gợi ý trên trang chủ" (tracking-pipeline) */
const home = ref(null)
const homeMsg = ref('')
const homeMode = (dim, code) => home.value?.cai_dat.find(s => s.gia_tri === dim + ':' + code)?.che_do || 'tu_dong'
async function setHome(value, mode, name) {
  homeMsg.value = ''
  try {
    await setHomeSetting(value, mode)
    home.value = await getHomeSettings()
    homeMsg.value = `Đã lưu: ${name} — ${{ tu_dong: 'tự động', uu_tien: 'ưu tiên', an: 'ẩn' }[mode]} trên trang chủ.`
  } catch (e) { homeMsg.value = 'Chưa lưu được: ' + e.message }
}
watch(days, load, { immediate: true })

/* Báo cáo tuần: mỗi người tự bật / tắt; KTS trưởng và admin xem thêm lịch sử gửi */
const isApprover = computed(() => hasRole(APPROVERS))
const optIn = ref(null)
const optBusy = ref(false)
const optMsg = ref('')
getWeeklyOptIn().then(r => { optIn.value = r.nhan }, () => {}) // without it the box just stays hidden
async function saveOptIn(on) {
  optBusy.value = true; optMsg.value = ''
  try {
    optIn.value = (await setWeeklyOptIn(on)).nhan
    optMsg.value = on ? 'Đã bật báo cáo tuần.' : 'Đã tắt báo cáo tuần.'
  } catch (e) { optMsg.value = e.message } finally { optBusy.value = false }
}
</script>

<style scoped>
.tr-demo { margin: 16px 0 0; padding: 12px 14px; border: 1px solid var(--accent); border-radius: var(--radius-md);
           color: var(--ink); font-size: 14px; background: color-mix(in oklab, var(--accent) 12%, transparent) }
.tr-demo code { font-size: 13px; overflow-wrap: anywhere }
.tr-bar { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: center; margin-top: 20px }
.tr-bar > .row { flex-wrap: wrap }
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

.bh-grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)) }
.bh-block { min-width: 0 }
.bh-h { margin: 0 0 8px; font-size: 13px; font-weight: 500; color: var(--ink-2) }
.bh-table { width: 100%; border-collapse: collapse; font-size: 13px; color: var(--ink-2) }
.bh-table th { text-align: left; font-weight: 400; font-size: 11px; color: var(--faint); padding: 4px 6px; border-bottom: 1px solid var(--line) }
.bh-table td { padding: 5px 6px; border-bottom: 1px solid var(--line-soft); overflow-wrap: anywhere }
.bh-table code, .bh-list code { font-size: 12px }
.bh-list { margin: 0; padding-left: 18px; display: grid; gap: 4px; font-size: 13px; color: var(--ink-2) }
.bh-list .num { color: var(--dim); margin-left: 4px }
.bh-from { display: block; color: var(--faint) }
.bh-anon { margin: 8px 0 0; color: var(--faint) }
@media (max-width: 600px) {
  .bh-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0) }
  .bh-table, .bh-table tbody, .bh-table tr, .bh-table td { display: block }
  .bh-table tr { padding: 6px 0; border-bottom: 1px solid var(--line-soft) }
  .bh-table td { display: flex; justify-content: space-between; gap: 10px; border: 0; padding: 2px 0 }
  .bh-table td::before { content: attr(data-k); color: var(--faint); font-size: 11px }
}
.tr-top a:focus-visible { outline: 2px solid var(--ink-2); outline-offset: 3px }
.tr-fresh { margin: 10px 0 0; color: var(--dim) }
.tr-groups { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px }
.tr-groups li { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap }
.tr-gshare { min-width: 3.5em; font-weight: 600 }
.tr-new { font-size: 12px; padding: 1px 8px; border-radius: 10px; background: var(--accent); color: var(--page) }
.tr-preview { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)) }
.tr-preview li { display: flex; flex-direction: column; gap: 6px }
.tr-preview img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: var(--radius-sm) }
</style>
