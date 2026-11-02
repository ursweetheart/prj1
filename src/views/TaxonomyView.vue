<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Đề xuất chiều phân loại mới</h1>
    <p class="lead" style="margin-top:10px">
      AI đề xuất từ mô tả ảnh, câu hỏi khách chưa được trả lời và lượt xem của khách đã đồng ý. Chỉ khi bạn chấp nhận,
      chiều mới mới được tạo, gắn nhãn cho cả thư viện và hiện thành bộ lọc trên trang Công trình.
    </p>

    <p v-if="done" class="panel small" style="margin-top:20px" role="status">
      Đã tạo chiều «{{ done.ten }}» ({{ done.gia_tri.length }} giá trị): gắn nhãn {{ done.gan_nhan }} không gian,
      {{ done.can_xem_lai.length }} cần xem lại.
      <router-link :to="'/cong-trinh#' + done.chieu + '=' + done.gia_tri[0]">Xem bộ lọc</router-link>
    </p>
    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-if="loading" class="small" style="margin-top:20px">Đang tải…</p>
    <p v-else-if="!items.length" class="small" style="margin-top:20px">Không có đề xuất nào đang chờ duyệt.</p>
    <p v-if="waiting" class="small" style="margin-top:8px">{{ waiting }} đề xuất khác đang chờ thêm bằng chứng (chưa đủ điểm).</p>

    <article v-for="c in items" :key="c.id" class="panel stack" style="margin-top:20px;gap:14px">
      <div class="field"><label :for="'ten' + c.id">Tên chiều</label>
        <input :id="'ten' + c.id" v-model="c.ten" class="txt"></div>
      <p v-if="c.bang_chung.mo_ta" class="small">{{ c.bang_chung.mo_ta }}</p>
      <div class="stack" style="gap:8px">
        <span class="small">Giá trị</span>
        <div class="row g10" style="flex-wrap:wrap">
          <input v-for="(v, i) in c.gia_tri" :key="i" v-model="c.gia_tri[i]" class="txt" style="width:180px"
                 :aria-label="'Giá trị ' + (i + 1) + ' của ' + c.ten">
        </div>
      </div>

      <dl class="score num small">
        <div><dt>Điểm</dt><dd>{{ pct(c.bang_chung.score) }}</dd></div>
        <div><dt>Độ phủ</dt><dd>{{ pct(c.bang_chung.coverage) }}</dd></div>
        <div><dt>Độ khác biệt</dt><dd>{{ pct(c.bang_chung.distinct) }}</dd></div>
        <div><dt>Nhu cầu</dt><dd>{{ pct(c.bang_chung.demand) }}</dd></div>
        <div><dt>Nguồn</dt><dd>{{ (c.bang_chung.nguon || []).map(n => SOURCE[n] || n).join(', ') }}</dd></div>
      </dl>
      <p v-if="c.bang_chung.ly_do" class="small">Kiểm tra của AI: {{ c.bang_chung.ly_do }}</p>

      <div v-if="c.vi_du.length" class="row g10" style="flex-wrap:wrap">
        <router-link v-for="s in c.vi_du" :key="s.id" :to="'/khong-gian/' + s.id" class="thumb" :title="s.relative_path">
          <img :src="imageUrl(s.relative_path)" :alt="spaceLabel(s.space_type) + ' ví dụ cho ' + c.ten" loading="lazy">
        </router-link>
      </div>

      <div class="row g10">
        <button class="btn btn-primary" type="button" :disabled="!!busy" @click="accept(c)">
          {{ busy === c.id ? 'Đang gắn nhãn cả thư viện…' : 'Chấp nhận' }}</button>
        <button class="btn btn-secondary" type="button" :disabled="!!busy" @click="reject(c)">Từ chối</button>
      </div>
    </article>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { acceptCandidate, imageUrl, listCandidates, rejectCandidate, spaceLabel } from '@/api'

const MARK = '[AI SINH - CHƯA DUYỆT] '
const SOURCE = { image: 'Ảnh', chat: 'Câu hỏi khách', behavior: 'Lượt xem' }
const items = ref([])
const waiting = ref(0)
const loading = ref(true)
const busy = ref(null) // id being decided; accepting runs Gemini over the whole library
const error = ref('')
const done = ref(null)
const pct = x => (x == null ? '—' : Math.round(x * 100) + '%')

async function load() {
  loading.value = true
  try {
    const r = await listCandidates()
    items.value = r.candidates.map(c => ({ ...c, ten: c.ten_de_xuat.replace(MARK, ''), gia_tri: [...(c.bang_chung.gia_tri || [])] }))
    waiting.value = r.cho_bang_chung
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

async function decide(c, call) {
  busy.value = c.id; error.value = ''; done.value = null
  try {
    const r = await call()
    items.value = items.value.filter(x => x.id !== c.id)
    return r
  } catch (e) { error.value = e.message }
  finally { busy.value = null }
}

async function accept(c) {
  const r = await decide(c, () => acceptCandidate(c.id, c.ten.trim(), c.gia_tri.map(v => v.trim()).filter(Boolean)))
  if (r) done.value = { ...r, ten: c.ten.trim() }
}
const reject = c => decide(c, () => rejectCandidate(c.id))

onMounted(load)
</script>

<style scoped>
.txt { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius-md);
  padding: 10px 12px; min-height: 42px; max-width: 100%; color-scheme: dark }
.txt:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring) }
.panel { border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px }
.score { display: flex; flex-wrap: wrap; gap: 8px 24px; margin: 0 }
.score dt { color: var(--dim) }
.score dd { margin: 0; color: var(--ink) }
.thumb { border-radius: var(--radius-sm); overflow: hidden; display: block }
.thumb img { width: 140px; height: 100px; object-fit: cover; display: block }
</style>
