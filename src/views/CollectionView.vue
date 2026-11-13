<template>
  <main class="wrap col-page">
    <header class="projects-head">
      <div>
        <h1 class="projects-title">{{ shared ? 'Bộ sưu tập đã gửi' : 'Bộ sưu tập' }}</h1>
        <p class="projects-intro">
          <template v-if="shared">Những không gian khách đã chọn và gửi cho kiến trúc sư D3 Studio, kèm ghi chú của khách.</template>
          <template v-else>Những không gian bạn đã lưu bằng trái tim. Ghi chú điều bạn thích ở mỗi ảnh, rồi gửi cho kiến trúc sư.</template>
        </p>
      </div>
    </header>

    <p v-if="error" class="col-note" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="col-note">Đang tải…</p>

    <!-- ── shared, read-only view of a sent brief ── -->
    <template v-else-if="shared">
      <p v-if="sent?.tom_tat?.line" class="col-summary">{{ sent.tom_tat.line }}</p>
      <p class="col-note">Gửi ngày {{ new Date(sent.created_at).toLocaleDateString('vi-VN') }} · {{ cards.length }} ảnh</p>
      <ul class="col-grid">
        <li v-for="c in cards" :key="c.apiId" class="col-item">
          <router-link class="col-thumb" :to="'/khong-gian/' + c.apiId">
            <img :src="c.img" :alt="c.space + ' — ' + c.projectName" loading="lazy" decoding="async">
          </router-link>
          <p class="col-meta">{{ c.space }} · {{ c.projectName }}</p>
          <p v-if="notes[c.apiId]" class="col-quote">“{{ notes[c.apiId] }}”</p>
        </li>
      </ul>
    </template>

    <!-- ── the visitor's own collection ── -->
    <template v-else>
      <section v-if="!cards.length" class="col-empty">
        <p>Chưa có ảnh nào. Bấm trái tim trên một không gian để lưu vào đây.</p>
        <router-link class="pv-nav-link glow-hover" to="/khong-gian">Xem các không gian <span aria-hidden="true">→</span></router-link>
      </section>

      <template v-else>
        <div class="col-bar">
          <p class="col-note num">{{ cards.length }} ảnh</p>
          <button class="btn btn-primary" type="button" :aria-expanded="String(showBrief)" @click="openBrief">
            Gửi cho kiến trúc sư
          </button>
        </div>
        <p v-if="!session.user" class="col-invite">
          Bộ sưu tập đang được giữ trong trình duyệt này.
          <router-link :to="{ path: '/dang-nhap', query: { next: '/bo-suu-tap' } }">Đăng ký để giữ bộ sưu tập</router-link>
          và xem lại trên máy khác.
        </p>
        <p v-if="collection.error" class="field-err" role="alert">{{ collection.error }}</p>

        <section v-if="showBrief" ref="briefEl" class="col-brief">
          <BriefForm :items="sendable" />
        </section>

        <ul class="col-grid">
          <li v-for="c in cards" :key="c.apiId" class="col-item">
            <router-link class="col-thumb" :to="'/khong-gian/' + c.apiId">
              <img :src="c.img" :alt="c.space + ' — ' + c.projectName" loading="lazy" decoding="async">
            </router-link>
            <div class="col-row">
              <p class="col-meta">{{ c.space }} · {{ c.projectName }}</p>
              <button class="col-remove" type="button" :aria-label="'Bỏ ảnh ' + c.space + ' khỏi bộ sưu tập'"
                      @click="remove(c.apiId)">Bỏ</button>
            </div>
            <label class="sr-only" :for="'note-' + c.apiId">Ghi chú cho ảnh {{ c.space }}</label>
            <textarea :id="'note-' + c.apiId" class="col-textarea" rows="2" maxlength="300"
                      placeholder="Bạn thích gì ở ảnh này?" :value="noteOf(c.apiId)"
                      @blur="e => setNote(c.apiId, e.target.value)"></textarea>
          </li>
        </ul>
      </template>
    </template>
  </main>
</template>

<script setup>
/* /bo-suu-tap: bộ sưu tập của khách (UC07). /bo-suu-tap/xem/:ma: bản đã gửi cho kiến trúc sư, chỉ xem (UC08). */
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BriefForm from '@/components/BriefForm.vue'
import { getSharedCollection, getSpacesByIds, session, toCard } from '@/api'
import { collection, remove, setNote } from '@/lib/collection'
import { projectBySlug } from '@/data/projects'
import { slugOf } from '@/lib/projectSpaces'

const route = useRoute()
const shared = computed(() => !!route.params.ma)
const rows = ref([])          // space rows to show
const sent = ref(null)        // the shared copy
const notes = ref({})         // space id -> note, for the shared view
const loading = ref(true)
const error = ref('')
const showBrief = ref(false)
const briefEl = ref(null)

// project name from the site when the photo belongs to a site project, else the folder name
const named = r => {
  const c = toCard(r)
  return { ...c, projectName: projectBySlug(slugOf(r.relative_path))?.name || c.projectName }
}
const cards = computed(() => rows.value.map(named))
const noteOf = id => collection.items.find(i => i.space_id === id)?.ghi_chu || ''
// what the brief sends: the shown (still published) photos, in collection order, with their notes
const sendable = computed(() => cards.value.map(c => ({ space_id: c.apiId, ghi_chu: noteOf(c.apiId) || null })))

async function loadShared(code) {
  loading.value = true; error.value = ''
  try {
    sent.value = await getSharedCollection(code)
    rows.value = sent.value.items
    notes.value = Object.fromEntries(sent.value.items.map(i => [i.id, i.ghi_chu]))
  } catch (e) {
    error.value = e.status === 404 || e.status === 422 ? 'Không tìm thấy bộ sưu tập' : e.message
  } finally { loading.value = false }
}

let asked = null // the id list last fetched; null = nothing fetched yet
async function loadOwn() {
  const ids = collection.items.map(i => i.space_id)
  const key = ids.join(',')
  if (key === asked) return // a note edit does not refetch
  asked = key
  error.value = ''
  try {
    const got = await getSpacesByIds(ids)
    if (asked !== key) return
    const byId = new Map(got.map(r => [r.id, r]))
    rows.value = ids.map(id => byId.get(id)).filter(Boolean) // unpublished spaces drop out
  } catch (e) { error.value = 'Chưa tải được bộ sưu tập: ' + e.message } finally { loading.value = false }
}

watch(() => route.params.ma, code => { if (code) loadShared(code) }, { immediate: true })
watch(() => [shared.value, collection.ready, collection.items.map(i => i.space_id).join(',')],
      ([isShared, ready]) => { if (!isShared && ready) loadOwn() }, { immediate: true })

async function openBrief() {
  showBrief.value = !showBrief.value
  if (showBrief.value) { await nextTick(); briefEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
}
</script>

<style scoped>
/* visually hidden label, as in SpacesView */
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.col-page { padding-bottom: clamp(48px, 7vw, 96px) }
.col-note { color: var(--dim); font-size: 14px; margin: 0 }
.col-summary { margin: 0 0 8px; font-size: clamp(17px, 1.6vw, 20px); color: var(--ink) }
.col-empty { display: grid; gap: 16px; justify-items: start; padding: 32px 0 }
.col-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
           padding-bottom: 16px; border-bottom: 1px solid var(--line-soft) }
.col-invite { margin: 16px 0 0; font-size: 14px; color: var(--dim) }
.col-invite a { color: var(--ink); text-decoration: underline; text-underline-offset: 3px }
.col-brief { margin-top: 28px; padding: clamp(20px, 3vw, 32px); border: 1px solid var(--line); border-radius: var(--radius-md);
             background: var(--panel); scroll-margin-top: 120px }
.col-grid { list-style: none; padding: 0; margin: 28px 0 0; display: grid; gap: clamp(20px, 2.4vw, 32px);
            grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)) }
.col-item { display: grid; gap: 10px; align-content: start; min-width: 0 }
.col-thumb { display: block; aspect-ratio: 4 / 3; overflow: hidden; background: var(--panel); border-radius: var(--radius-sm) }
.col-thumb img { width: 100%; height: 100%; object-fit: cover; display: block }
.col-thumb:focus-visible { outline: 2px solid var(--ink-2); outline-offset: 3px }
.col-row { display: flex; align-items: baseline; justify-content: space-between; gap: 12px }
.col-meta { margin: 0; font-size: 13px; color: var(--dim); min-width: 0; overflow-wrap: anywhere }
.col-remove { background: none; border: 0; padding: 4px 0; color: var(--faint); font: inherit; font-size: 13px; cursor: pointer;
              text-decoration: underline; text-underline-offset: 3px }
.col-remove:hover, .col-remove:focus-visible { color: var(--ink) }
.col-textarea { width: 100%; min-width: 0; resize: vertical; background: var(--panel); color: var(--ink);
                border: 1px solid var(--line); border-radius: var(--radius-md); padding: 10px 12px; font: inherit; font-size: 14px }
.col-textarea:focus-visible { border-color: var(--accent); box-shadow: var(--focus-ring); outline: none }
.col-quote { margin: 0; font-size: 14px; color: var(--ink-2); font-style: italic; overflow-wrap: anywhere }
</style>
