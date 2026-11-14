<template>
  <main class="wrap page-top qz-page">
    <header class="projects-head">
      <div>
        <h1 class="projects-title">Trắc nghiệm phong cách</h1>
        <p class="projects-intro">
          Chọn ảnh bạn thích hơn trong mỗi cặp. Sau vài câu, D3 Studio gợi ý phong cách hợp với bạn và những không gian gần với lựa chọn của bạn.
        </p>
      </div>
    </header>

    <!-- static build: no backend -->
    <section v-if="state === 'offline'" class="qz-box">
      <p>Trắc nghiệm phong cách cần bản đầy đủ của website (có máy chủ AI). Bạn vẫn có thể xem các dự án của D3 Studio.</p>
      <router-link class="pv-nav-link glow-hover" to="/du-an">Xem dự án <span aria-hidden="true">→</span></router-link>
    </section>

    <section v-else-if="state === 'unavailable'" class="qz-box">
      <p>Trắc nghiệm chưa sẵn sàng: chưa có đủ ảnh đã đăng ở nhiều phong cách. Mời bạn quay lại sau, hoặc xem các không gian hiện có.</p>
      <router-link class="pv-nav-link glow-hover" to="/khong-gian">Xem các không gian <span aria-hidden="true">→</span></router-link>
    </section>

    <section v-else-if="state === 'start' || state === 'loading'" class="qz-box">
      <p>{{ pairsHint }} Không cần tài khoản, không có câu trả lời đúng hay sai.</p>
      <button class="btn btn-primary" type="button" :disabled="state === 'loading'" @click="begin">
        {{ state === 'loading' ? 'Đang chuẩn bị…' : 'Bắt đầu' }}
      </button>
      <p v-if="error" class="field-err" role="alert">{{ error }}</p>
    </section>

    <!-- ── one question ── -->
    <section v-else-if="state === 'question'" class="qz-q" aria-labelledby="qz-progress">
      <div class="qz-top">
        <p id="qz-progress" class="qz-progress num" aria-live="polite">Câu {{ idx + 1 }}/{{ pairs.length }}</p>
        <div class="qz-bar" aria-hidden="true"><span :style="{ width: (100 * idx / pairs.length) + '%' }"></span></div>
      </div>
      <p class="qz-ask">Bạn thích không gian nào hơn?</p>
      <div class="qz-pair">
        <button v-for="(p, side) in sides" :key="p.id" ref="choiceEls" class="qz-choice" type="button"
                :class="{ 'is-picked': answers[idx] === p.id }" :aria-pressed="String(answers[idx] === p.id)"
                @click="choose(p.id)">
          <img :src="imageUrl(p.relative_path)" :alt="altOf(p)" decoding="async">
          <span class="qz-key" aria-hidden="true">{{ side + 1 }}</span>
          <span class="sr-only">Chọn ảnh {{ side + 1 }}</span>
        </button>
      </div>
      <div class="qz-actions">
        <button class="btn btn-ghost" type="button" :disabled="idx === 0" @click="back">← Quay lại</button>
        <button class="btn btn-ghost" type="button" @click="skip">Bỏ qua</button>
      </div>
      <p class="qz-hint only-desk">Phím 1 / 2 để chọn, Esc để quay lại.</p>
      <p v-if="error" class="field-err" role="alert">{{ error }}</p>
    </section>

    <section v-else-if="state === 'too_few'" class="qz-box">
      <p role="alert">Hãy chọn ít nhất 2 ảnh để có kết quả. Bạn có thể quay lại các câu hỏi hoặc làm lại với ảnh khác.</p>
      <div class="row g10">
        <button class="btn btn-secondary" type="button" @click="reopen">← Quay lại câu hỏi</button>
        <button class="btn btn-primary" type="button" @click="begin">Làm lại</button>
      </div>
    </section>

    <!-- ── the result ── -->
    <section v-else-if="state === 'result' && current" class="qz-result" aria-labelledby="qz-result-title">
      <h2 id="qz-result-title" class="qz-h2">Phong cách phù hợp nhất với bạn</h2>
      <ul class="qz-styles">
        <li v-for="s in current.phong_cach" :key="s.ma">
          <div class="qz-style-head">
            <span class="qz-style-name">{{ s.ten }}</span>
            <span class="num">{{ s.ti_le }}%</span>
          </div>
          <div class="qz-bar" aria-hidden="true"><span :style="{ width: s.ti_le + '%' }"></span></div>
          <router-link class="qz-more" :to="{ path: '/khong-gian', hash: '#phong_cach=' + s.ma }">
            Xem thêm phong cách {{ s.ten }} <span aria-hidden="true">→</span>
          </router-link>
        </li>
      </ul>

      <div class="qz-bar-row">
        <button class="btn btn-primary" type="button" :disabled="saving" @click="onSaveResult">
          {{ quiz.status === 'saving' ? 'Đang lưu…' : 'Lưu kết quả' }}
        </button>
        <button class="btn btn-secondary" type="button" @click="begin">Làm lại</button>
      </div>
      <div v-if="savedNote" class="form-ok" role="status"><span class="dot" aria-hidden="true"></span><p style="margin:0">Đã lưu kết quả</p></div>
      <p v-else-if="!session.user" class="qz-hint">Đăng nhập để lưu kết quả vào tài khoản và xem lại trên máy khác.</p>
      <p v-if="quiz.error" class="field-err" role="alert">{{ quiz.error }}</p>

      <template v-if="cards.length">
        <div class="qz-sugg-head">
          <h2 class="qz-h2">Không gian gợi ý cho bạn</h2>
          <button class="btn btn-ghost" type="button" @click="saveAll">Lưu tất cả vào bộ sưu tập</button>
        </div>
        <p v-if="allNote" class="qz-hint" role="status">{{ allNote }}</p>
        <p v-if="collection.error" class="field-err" role="alert">{{ collection.error }}</p>
        <div class="qz-grid">
          <SpaceTile v-for="c in cards" :key="c.apiId" :space="c" />
        </div>
      </template>
    </section>
  </main>
</template>

<script setup>
/* /trac-nghiem: trắc nghiệm phong cách (UC06, seq-12). Máy chủ chọn cặp ảnh và chấm điểm; trang chỉ gửi lại các cặp
 * đã hiện và ảnh đã chọn. Kết quả gần nhất giữ trong trình duyệt; đăng nhập thì lưu vào tài khoản (lib/quiz.js). */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SpaceTile from '@/components/SpaceTile.vue'
import { getQuiz, imageUrl, postQuizResult, session, toCard } from '@/api'
import { collection, add, has } from '@/lib/collection'
import { aiAvailable } from '@/lib/projectSpaces'
import { quiz, rememberLast, saveResult, startQuiz, trackPick } from '@/lib/quiz'

const router = useRouter()
const state = ref('start')   // offline | unavailable | start | loading | question | too_few | result
const pairs = ref([])        // [{a, b}] from GET /quiz
const answers = ref([])      // per question: chosen space id, null = skipped, undefined = not answered yet
const idx = ref(0)
const error = ref('')
const fresh = ref(null)      // a result made on this page just now
const allNote = ref('')
const choiceEls = ref([])

const sides = computed(() => pairs.value[idx.value] ? [pairs.value[idx.value].a, pairs.value[idx.value].b] : [])
const pairsHint = 'Khoảng 6 câu, mỗi câu hai ảnh.'
const altOf = p => p.alt_text || p.caption || 'Ảnh không gian nội thất'

// what to show: the result just made, else the newer of the account's saved one and this browser's last one
const time = v => (v ? Date.parse(v) || 0 : 0)
const current = computed(() => {
  if (fresh.value) return fresh.value
  const saved = quiz.saved, last = quiz.last
  if (saved && (!last || time(saved.luu_luc) >= time(last.at))) return saved
  return last?.ket_qua || saved || null
})
const cards = computed(() => (current.value?.goi_y || []).map(toCard))
const saving = computed(() => quiz.status === 'saving')
const savedNote = computed(() => !!session.user && (quiz.status === 'saved' || (!fresh.value && current.value === quiz.saved)))

async function begin() {
  state.value = 'loading'; error.value = ''; allNote.value = ''
  try {
    const out = await getQuiz()
    pairs.value = out.cau_hoi
    answers.value = Array(out.cau_hoi.length).fill(undefined)
    idx.value = 0
    state.value = 'question'
    focusFirst()
  } catch (e) {
    if (e.status === 409) { state.value = 'unavailable'; return }
    state.value = 'start'
    error.value = 'Chưa tải được câu hỏi, vui lòng thử lại.'
  }
}

function focusFirst() { nextTick(() => choiceEls.value?.[0]?.focus()) }

function choose(id) {
  if (answers.value[idx.value] !== id) trackPick(id) // re-confirming the same photo after "Quay lại" is not a new pick
  answers.value[idx.value] = id
  next()
}
function skip() { answers.value[idx.value] = null; next() }
function back() { if (idx.value > 0) { idx.value--; focusFirst() } }
function reopen() { idx.value = pairs.value.length - 1; state.value = 'question'; focusFirst() }

function next() {
  if (idx.value < pairs.value.length - 1) { idx.value++; focusFirst(); return }
  finish()
}

async function finish() {
  const chon = answers.value.filter(v => Number.isInteger(v))
  if (chon.length < 2) { state.value = 'too_few'; return }
  const answersSent = { cap: pairs.value.map(p => [p.a.id, p.b.id]), chon }
  state.value = 'loading'
  try {
    const out = await postQuizResult(answersSent)
    rememberLast(answersSent, out)
    fresh.value = out
    state.value = 'result'
    window.scrollTo?.({ top: 0 })
  } catch {
    state.value = 'question'
    error.value = 'Chưa tính được kết quả, vui lòng thử lại.'
  }
}

async function onSaveResult() {
  const r = await saveResult()
  if (r === 'login') router.push({ path: '/dang-nhap', query: { next: '/trac-nghiem' } })
}

async function saveAll() {
  allNote.value = ''
  let added = 0
  for (const c of cards.value) {
    if (has(c.apiId)) continue
    if (!(await add(c.apiId))) break // full, or the server refused: collection.error says why
    added++
  }
  allNote.value = added ? `Đã thêm ${added} ảnh vào bộ sưu tập.` : collection.error ? '' : 'Các ảnh này đã có trong bộ sưu tập.'
}

function onKey(e) {
  if (state.value !== 'question' || e.altKey || e.ctrlKey || e.metaKey) return
  if (e.target?.closest?.('input, textarea, select')) return
  if (e.key === '1' || e.key === '2') { const p = sides.value[Number(e.key) - 1]; if (p) { e.preventDefault(); choose(p.id) } }
  else if (e.key === 'Escape') { e.preventDefault(); back() }
}

onMounted(async () => {
  startQuiz()
  window.addEventListener('keydown', onKey)
  if (!(await aiAvailable())) { state.value = 'offline'; return }
  if (current.value) state.value = 'result'
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
// the account's saved result arrives after the page opened (GET /quiz/me): show it if no attempt has started
watch(current, v => { if (v && state.value === 'start') state.value = 'result' })
</script>

<style scoped>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.only-desk { display: none }
@media (min-width: 1024px) { .only-desk { display: block } }

.qz-page { padding-bottom: clamp(48px, 7vw, 96px) }
.qz-box { display: grid; gap: 16px; justify-items: start; max-width: 640px; padding: 8px 0 32px }
.qz-box p { margin: 0 }
.qz-hint { margin: 0; font-size: 14px; color: var(--dim) }
.qz-h2 { margin: 0; font-size: clamp(20px, 2vw, 26px); font-weight: 600 }

.qz-top { display: flex; align-items: center; gap: 16px; max-width: 960px }
.qz-progress { margin: 0; font-size: 14px; color: var(--dim); white-space: nowrap }
.qz-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--line-soft); overflow: hidden }
.qz-bar span { display: block; height: 100%; background: var(--accent); transition: width .25s ease }
@media (prefers-reduced-motion: reduce) { .qz-bar span { transition: none } }
.qz-ask { margin: 20px 0 16px; font-size: clamp(18px, 1.8vw, 22px); color: var(--ink) }

.qz-pair { display: grid; grid-template-columns: 1fr; gap: 14px; max-width: 960px }
@media (min-width: 600px) { .qz-pair { grid-template-columns: 1fr 1fr; gap: 20px } }
.qz-choice { position: relative; display: block; padding: 0; border: 2px solid transparent; border-radius: var(--radius-md, 12px);
             overflow: hidden; background: var(--panel); cursor: pointer; aspect-ratio: 4 / 3 }
.qz-choice img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .3s ease }
.qz-choice:hover img { transform: scale(1.02) }
@media (prefers-reduced-motion: reduce) { .qz-choice img { transition: none } .qz-choice:hover img { transform: none } }
.qz-choice:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px }
.qz-choice.is-picked { border-color: var(--accent) }
.qz-key { position: absolute; left: 10px; top: 10px; min-width: 28px; height: 28px; display: grid; place-items: center;
          border-radius: 14px; background: rgba(20, 20, 19, .7); color: #fff; font-size: 14px; font-weight: 600 }
.qz-actions { display: flex; justify-content: space-between; gap: 12px; max-width: 960px; margin-top: 16px }
.qz-q .qz-hint { margin-top: 8px }

.qz-result { display: grid; gap: 20px }
.qz-styles { list-style: none; margin: 0; padding: 0; display: grid; gap: 18px; max-width: 640px }
.qz-style-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px }
.qz-style-name { font-size: clamp(20px, 2.2vw, 28px); font-weight: 600; color: var(--ink) }
.qz-styles .qz-bar { display: block; flex: none }
.qz-more { display: inline-block; margin-top: 8px; font-size: 14px; color: var(--ink); text-decoration: underline; text-underline-offset: 3px }
.qz-bar-row { display: flex; flex-wrap: wrap; gap: 10px }
.qz-sugg-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
                margin-top: 16px; padding-top: 24px; border-top: 1px solid var(--line-soft) }
.qz-grid { display: grid; grid-template-columns: 1fr; gap: 0 20px }
@media (min-width: 600px) { .qz-grid { grid-template-columns: repeat(2, 1fr) } }
@media (min-width: 1024px) { .qz-grid { grid-template-columns: repeat(4, 1fr) } }
</style>
