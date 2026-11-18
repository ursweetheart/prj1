<template>
  <section>
    <h2 class="sr-only">Đề xuất chiều phân loại mới</h2>
    <p class="lead" style="margin-top:0">
      AI đề xuất từ mô tả ảnh, câu hỏi khách chưa được trả lời và lượt xem của khách đã đồng ý. Chỉ khi bạn chấp nhận,
      chiều mới mới được tạo, gắn nhãn cho cả thư viện và hiện thành bộ lọc trên trang Không gian.
    </p>

    <p v-if="done" class="panel small" style="margin-top:20px" role="status">
      Đã tạo chiều «{{ done.ten }}» ({{ done.gia_tri.length }} giá trị): gắn nhãn {{ done.gan_nhan }} không gian,
      {{ done.can_xem_lai.length }} cần xem lại.
      <router-link :to="'/khong-gian#' + done.chieu + '=' + done.gia_tri[0]">Xem bộ lọc</router-link>
    </p>
    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-if="loading" class="small" style="margin-top:20px">Đang tải…</p>
    <p v-else-if="!items.length && !valueItems.length" class="small" style="margin-top:20px">Không có đề xuất nào đang chờ duyệt.</p>
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

    <!-- review-tag-autocomplete: words reviewers typed for a room type / style that no value covers -->
    <template v-if="valueItems.length || valueDone">
      <h2 class="h-4" style="margin-top:36px">Giá trị được gợi ý</h2>
      <p class="small">Kiến trúc sư gõ khi duyệt ảnh; các ảnh này đang tạm để «Khác» cho tới khi bạn quyết định.</p>
      <p v-if="valueDone" class="panel small" style="margin-top:12px" role="status">{{ valueDone }}</p>
      <article v-for="c in valueItems" :key="c.id" class="panel stack" style="margin-top:16px;gap:12px">
        <p class="small" style="margin:0">{{ DIM_VI[c.bang_chung.chieu] }} · gõ là «{{ c.ten_de_xuat }}» ·
          {{ c.cho.length }} ảnh đang chờ</p>
        <div v-if="c.bang_chung.ai" class="ai stack small">
          <p v-if="c.bang_chung.ai.ly_do"><strong>Kiểm tra của AI:</strong> {{ c.bang_chung.ai.ly_do }}</p>
          <p v-if="c.bang_chung.ai.gan_nhat || c.bang_chung.ai.khac_biet"><strong>Gần nhất:</strong>
            <template v-if="c.bang_chung.ai.gan_nhat">«{{ valueName(c.bang_chung.chieu, c.bang_chung.ai.gan_nhat) }}»</template>
            <template v-if="c.bang_chung.ai.khac_biet"> · {{ c.bang_chung.ai.khac_biet }}</template></p>
          <div v-if="c.bang_chung.ai.dac_trung?.length"><strong>Đặc trưng nhận biết:</strong>
            <ul><li v-for="(f, i) in c.bang_chung.ai.dac_trung" :key="i">{{ f }}</li></ul></div>
          <p v-if="c.bang_chung.ai.anh_khop != null" :class="c.bang_chung.ai.anh_khop ? 'ok' : 'bad'">
            <strong>{{ c.bang_chung.ai.anh_khop ? '✓ Ảnh khớp' : '⚠ Ảnh có vẻ không khớp' }}:</strong> {{ c.bang_chung.ai.nhan_xet_anh }}</p>
        </div>
        <div class="field"><label :for="'vt' + c.id">Tên giá trị</label>
          <input :id="'vt' + c.id" v-model="c.ten" class="txt"></div>
        <div class="field"><label :for="'vm' + c.id">Mô tả <span v-if="c.aiDraft" class="small">(AI soạn nháp, hãy sửa)</span></label>
          <textarea :id="'vm' + c.id" v-model="c.mo_ta" class="txt" rows="2"></textarea></div>
        <div class="field"><label :for="'vs' + c.id">Từ đồng nghĩa, cách nhau bằng dấu phẩy</label>
          <input :id="'vs' + c.id" v-model="c.syn" class="txt"></div>
        <ul v-if="c.cho.length" class="waiting">
          <li v-for="s in c.cho" :key="s.id">
            <router-link :to="'/khong-gian/' + s.id" class="thumb" :title="s.relative_path">
              <img :src="imageUrl(s.relative_path)" :alt="'Ảnh đang chờ «' + c.ten_de_xuat + '»'" loading="lazy">
            </router-link>
            <div v-if="draftOf(c, s)" class="small">
              <strong>Mô tả ảnh sẽ đổi thành:</strong> {{ draftOf(c, s) }}
              <span class="faint">Hiện tại: {{ s.caption }}</span>
            </div>
            <div v-else class="small faint">Mô tả ảnh giữ nguyên{{ c.bang_chung.mo_ta_anh?.[s.id] ? ' (đã có người sửa)' : '' }}.</div>
          </li>
        </ul>
        <div class="row g10" style="flex-wrap:wrap;align-items:center">
          <button class="btn btn-primary" type="button" :disabled="!!busy || !c.ten.trim()" @click="acceptValue(c)">Tạo giá trị</button>
          <TagInput v-model="c.mapTo" :values="dimValues[c.bang_chung.chieu] || []" :id="'vmap' + c.id" :allow-new="false"
                    :label="'Gộp vào giá trị có sẵn'" style="max-width:240px" />
          <button class="btn btn-secondary" type="button" :disabled="!!busy || !c.mapTo" @click="mapValue(c)">Gộp vào</button>
          <button class="btn btn-ghost" type="button" :disabled="!!busy" @click="rejectValue(c)">Từ chối</button>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup>
/* Tab "Đề xuất của AI" of /quan-tri/phan-loai: AI-proposed dimensions awaiting the lead architect (seq-15). */
import { onMounted, ref } from 'vue'
import { acceptCandidate, acceptValueCandidate, getTaxonomy, imageUrl, listCandidates, mapValueCandidate, rejectCandidate,
  rejectValueCandidate, spaceLabel } from '@/api'
import TagInput from '@/components/TagInput.vue'

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
    valueItems.value = (r.gia_tri || []).map(c => ({ ...c, ten: c.ten_de_xuat, mo_ta: c.bang_chung.mo_ta || '',
      aiDraft: !!c.bang_chung.mo_ta, syn: (c.bang_chung.tu_dong_nghia || []).join(', '), mapTo: '' }))
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

/* value suggestions (review-tag-autocomplete) */
const DIM_VI = { khong_gian: 'Loại không gian', phong_cach: 'Phong cách' }
const valueItems = ref([])
const valueDone = ref('')
const dimValues = ref({})
/* the caption the AI drafted for this photo, as it will be written on accept: only while nobody changed the caption,
   and with the typed word replaced by the name in the field (same rule as the server) */
const draftOf = (c, s) => {
  const d = c.bang_chung.mo_ta_anh?.[s.id]
  return d && d.cu === s.caption ? d.caption.replaceAll(c.ten_de_xuat, c.ten.trim() || c.ten_de_xuat) : ''
}
const valueName = (dim, code) => (dimValues.value[dim] || []).find(v => v.ma_dinh_danh === code)?.ten || code
async function decideValue(c, call, message) {
  valueDone.value = ''
  const r = await decide(c, call)
  if (!r) return
  valueItems.value = valueItems.value.filter(x => x.id !== c.id)
  valueDone.value = message(r)
  loadValues() // a new value or synonym: the map pickers should know it
}
const acceptValue = c => decideValue(c,
  () => acceptValueCandidate(c.id, { ten: c.ten.trim(), mo_ta: c.mo_ta.trim() || null,
    tu_dong_nghia: c.syn.split(',').map(x => x.trim()).filter(Boolean) }),
  r => `Đã tạo «${r.gia_tri.ten}», ${r.da_chuyen.length} ảnh chuyển sang giá trị này, viết lại mô tả ${r.viet_lai_mo_ta.length} ảnh.`)
const mapValue = c => {
  const v = (dimValues.value[c.bang_chung.chieu] || []).find(x => x.ma_dinh_danh === c.mapTo)
  return decideValue(c, () => mapValueCandidate(c.id, v.id),
    r => `«${c.ten_de_xuat}» thành từ đồng nghĩa của «${r.gia_tri.ten}», ${r.da_chuyen.length} ảnh chuyển sang.`)
}
const rejectValue = c => {
  if (!window.confirm(`Từ chối «${c.ten_de_xuat}»? ${c.cho.length} ảnh sẽ giữ «Khác».`)) return
  return decideValue(c, () => rejectValueCandidate(c.id), () => `Đã từ chối «${c.ten_de_xuat}».`)
}
const loadValues = () => getTaxonomy()
  .then(dims => { dimValues.value = Object.fromEntries(dims.map(d => [d.ma_dinh_danh, d.values])) })
  .catch(() => {})

onMounted(() => { load(); loadValues() })
</script>

<style scoped>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.panel { border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px }
.score { display: flex; flex-wrap: wrap; gap: 8px 24px; margin: 0 }
.score dt { color: var(--dim) }
.score dd { margin: 0; color: var(--ink) }
.thumb { border-radius: var(--radius-sm); overflow: hidden; display: block }
.ai { gap: 6px; color: var(--dim) }
.waiting { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px }
.waiting li { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap }
.waiting li > div { flex: 1 1 240px; display: grid; gap: 4px }
.faint { color: var(--faint) }
.ai p, .ai ul { margin: 0 }
.ai ul { padding-left: 20px }
.ai strong { color: var(--ink); font-weight: 500 }
.ai .ok strong { color: var(--success) }
.ai .bad strong { color: var(--warn) }
.thumb img { width: 140px; height: 100px; object-fit: cover; display: block }
</style>
