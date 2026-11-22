<template>
  <main class="wrap wrap-wide page-top us-page">
    <p class="eyebrow">Quản trị</p>
    <h1 class="h-2" style="margin-top:10px">Tài khoản</h1>
    <p class="lead" style="margin-top:10px">
      Đổi vai trò có hiệu lực ngay ở lần thao tác tiếp theo của người đó. Khoá tài khoản thì người đó bị đăng xuất và không đăng nhập lại được.
    </p>

    <!-- seq-19 b1-8: the account is created with its role; the person sets a password from the emailed link -->
    <form class="us-invite" aria-labelledby="us-inv-h" @submit.prevent="invite">
      <h2 id="us-inv-h" class="h-4">Mời tài khoản</h2>
      <div class="us-inv-row">
        <label class="sr-only" for="us-inv-email">Email người được mời</label>
        <input id="us-inv-email" v-model.trim="inv.email" class="txt us-inv-email" type="email" placeholder="email@congty.vn"
               required :aria-invalid="!!inv.error" :aria-describedby="inv.error ? 'us-inv-err' : null">
        <label class="sr-only" for="us-inv-name">Họ tên (không bắt buộc)</label>
        <input id="us-inv-name" v-model="inv.ho_ten" class="txt" type="text" maxlength="100" placeholder="Họ tên (không bắt buộc)">
        <label class="sr-only" for="us-inv-role">Vai trò</label>
        <select id="us-inv-role" v-model="inv.role" class="txt">
          <option v-for="(label, r) in ROLE_VI" :key="r" :value="r">{{ label }}</option>
        </select>
        <button class="btn btn-primary" :disabled="busy">Gửi lời mời</button>
      </div>
      <p v-if="inv.error" id="us-inv-err" class="field-err" role="alert">{{ inv.error }}</p>
    </form>
    <div v-if="link" class="us-link" role="status">
      <p class="small" style="margin:0">Chưa cấu hình email: gửi liên kết này cho <strong>{{ link.email }}</strong> (dùng một lần, trong 72 giờ).</p>
      <div class="us-inv-row">
        <label class="sr-only" for="us-link-val">Liên kết mời</label>
        <input id="us-link-val" class="txt us-inv-email" :value="link.url" readonly @focus="$event.target.select()">
        <button class="btn btn-secondary" type="button" @click="copyLink">{{ link.copied ? 'Đã sao chép' : 'Sao chép' }}</button>
      </div>
    </div>

    <div class="us-bar">
      <label class="sr-only" for="us-q">Tìm theo email</label>
      <input id="us-q" v-model="q" class="txt us-search" type="search" placeholder="Tìm theo email" @input="reloadSoon">
      <label class="sr-only" for="us-role">Lọc theo vai trò</label>
      <select id="us-role" v-model="roleFilter" class="txt us-role" @change="load">
        <option value="">Mọi vai trò</option>
        <option v-for="(label, r) in ROLE_VI" :key="r" :value="r">{{ label }}</option>
      </select>
    </div>
    <div class="us-chips" role="group" aria-label="Lọc theo trạng thái">
      <button v-for="s in STATES" :key="s.id" type="button" class="chip" :aria-pressed="String(state === s.id)"
              @click="state = s.id; load()">{{ s.label }}</button>
    </div>

    <p v-if="note" class="us-note" role="status">{{ note }}</p>
    <p v-if="error" class="field-err" role="alert">{{ error }}</p>
    <p v-if="loading && !items.length" class="small">Đang tải…</p>
    <p v-else-if="!items.length" class="small">Không có tài khoản nào.</p>

    <ul class="us-list">
      <li v-for="u in items" :key="u.id" class="us-item" :class="{ 'is-locked': u.bi_khoa }">
        <div class="us-who">
          <span class="us-email">{{ u.email }}</span>
          <!-- admin-tools: the account's full name, editable here -->
          <label class="sr-only" :for="'name-' + u.id">Họ tên của {{ u.email }}</label>
          <input :id="'name-' + u.id" class="txt us-name" type="text" maxlength="100" placeholder="Họ tên" :value="u.ho_ten || ''"
                 @change="saveName(u, $event.target.value)">
          <span v-if="u.la_toi" class="us-tag is-me">bạn</span>
          <span class="us-tags">
            <span v-for="m in u.dang_nhap" :key="m" class="us-tag">{{ METHOD[m] }}</span>
          </span>
          <span class="small us-since">Tạo {{ day(u.created_at) }}</span>
        </div>
        <div class="us-role-cell">
          <label class="sr-only" :for="'role-' + u.id">Vai trò của {{ u.email }}</label>
          <select :id="'role-' + u.id" class="txt" :value="u.role" :disabled="!u.doi_vai_tro_duoc || busy"
                  :aria-describedby="u.ly_do_khong ? 'why-' + u.id : null" @change="askRole(u, $event)">
            <option v-for="(label, r) in ROLE_VI" :key="r" :value="r">{{ label }}</option>
          </select>
        </div>
        <div class="us-state">
          <span v-if="u.chua_kich_hoat && !u.bi_khoa" class="us-tag is-pending">Chưa kích hoạt · mời {{ when(u.moi_luc) }}</span>
          <span v-else-if="u.bi_khoa" class="us-tag is-locked-tag">Bị khoá</span>
          <span v-else class="us-tag is-active">Đang hoạt động</span>
          <span v-if="u.bi_khoa && u.ly_do_khoa" class="small us-reason">{{ u.ly_do_khoa }}</span>
        </div>
        <div class="us-act">
          <template v-if="u.chua_kich_hoat && !u.bi_khoa">
            <button class="btn btn-secondary btn-sm" type="button" :disabled="busy" @click="resend(u)">Gửi lại lời mời</button>
            <button class="btn btn-ghost btn-sm us-danger" type="button" :disabled="busy" @click="cancel(u)">Huỷ lời mời</button>
          </template>
          <button v-else-if="u.bi_khoa" class="btn btn-secondary btn-sm" type="button" :disabled="busy" @click="unlock(u)">Mở khoá</button>
          <button v-if="!u.bi_khoa && !u.chua_kich_hoat" class="btn btn-ghost btn-sm us-danger" type="button" :disabled="!u.khoa_duoc || busy"
                  :aria-describedby="u.ly_do_khong ? 'why-' + u.id : null" @click="askLock(u, $event)">Khoá…</button>
        </div>
        <p v-if="u.ly_do_khong" :id="'why-' + u.id" class="small us-why">{{ u.ly_do_khong }}</p>
      </li>
    </ul>

    <section v-if="log.length" class="us-log" aria-labelledby="us-log-h">
      <h2 id="us-log-h" class="h-4">Gần đây</h2>
      <ol>
        <li v-for="l in log" :key="l.id">
          <span class="num us-dim">{{ when(l.created_at) }}</span>
          <span>{{ describe(l) }}</span>
          <span class="us-dim">{{ l.boi || 'lệnh hệ thống' }}</span>
        </li>
      </ol>
    </section>

    <!-- confirm a role change -->
    <dialog ref="roleEl" class="us-dialog" aria-labelledby="us-role-h" @close="onRoleClose">
      <form v-if="pendingRole" class="stack" style="gap:12px" @submit.prevent="confirmRole">
        <h2 id="us-role-h" class="h-4" style="margin:0">Đổi vai trò?</h2>
        <p style="margin:0">
          Đổi vai trò của <strong>{{ pendingRole.u.email }}</strong> từ «{{ ROLE_VI[pendingRole.u.role] }}» sang
          «{{ ROLE_VI[pendingRole.to] }}». Có hiệu lực ngay ở lần thao tác tiếp theo của người đó.
        </p>
        <p v-if="dlgError" class="field-err" role="alert">{{ dlgError }}</p>
        <div class="row g10">
          <button class="btn btn-primary" :disabled="busy">Đổi vai trò</button>
          <button class="btn btn-ghost" type="button" @click="roleEl.close()">Huỷ</button>
        </div>
      </form>
    </dialog>

    <!-- lock with a reason -->
    <dialog ref="lockEl" class="us-dialog" aria-labelledby="us-lock-h" @close="onLockClose">
      <form v-if="locking" class="stack" style="gap:12px" @submit.prevent="confirmLock">
        <h2 id="us-lock-h" class="h-4" style="margin:0">Khoá {{ locking.email }}?</h2>
        <p class="small" style="margin:0">Người này bị đăng xuất ngay và không đăng nhập lại được cho đến khi mở khoá.</p>
        <div class="field">
          <label for="us-reason">Lý do (bắt buộc)</label>
          <textarea id="us-reason" v-model="reason" class="txt" rows="3" maxlength="300" required
                    :aria-invalid="!!dlgError" aria-describedby="us-count us-err"></textarea>
          <span id="us-count" class="small num">{{ reason.trim().length }}/300</span>
          <span v-if="dlgError" id="us-err" class="field-err" role="alert">{{ dlgError }}</span>
        </div>
        <div class="row g10">
          <button class="btn btn-primary" :disabled="busy">Khoá tài khoản</button>
          <button class="btn btn-ghost" type="button" @click="lockEl.close()">Huỷ</button>
        </div>
      </form>
    </dialog>
  </main>
</template>

<script setup>
/* /quan-tri/tai-khoan (admin): accounts, roles, lock / unlock (UC24, seq-19 b16-19). The server enforces the guards
 * (never yourself, never the last active admin) and sends why a control is unavailable; the page only shows it. */
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ROLE_VI, cancelInvite, inviteUser, listUsers, lockUser, resendInvite, setUserName, setUserRole, unlockUser } from '@/api'

const METHOD = { mat_khau: 'Mật khẩu', google: 'Google', facebook: 'Facebook' }
const STATES = [{ id: '', label: 'Tất cả' }, { id: 'false', label: 'Đang hoạt động' }, { id: 'true', label: 'Bị khoá' }]
const ACTION = { doi_vai_tro: 'Đổi vai trò', khoa: 'Khoá', mo_khoa: 'Mở khoá', moi: 'Mời', gui_lai_moi: 'Gửi lại lời mời', huy_moi: 'Huỷ lời mời' }

const items = ref([])
const log = ref([])
const q = ref('')
const roleFilter = ref('')
const state = ref('')
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const note = ref('')
const dlgError = ref('')

const roleEl = ref(null)
const pendingRole = ref(null) // { u, to, select }
const lockEl = ref(null)
const locking = ref(null)
const reason = ref('')
let opener = null

const day = t => new Date(t).toLocaleDateString('vi-VN')
const when = t => new Date(t).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
function describe(l) {
  const head = `${ACTION[l.hanh_dong] || l.hanh_dong} ${l.tai_khoan || '(đã xoá)'}`
  if (l.hanh_dong === 'doi_vai_tro') return `${head}: ${ROLE_VI[l.truoc?.role] || l.truoc?.role} → ${ROLE_VI[l.sau?.role] || l.sau?.role}`
  if (l.hanh_dong === 'khoa') return `${head}: ${l.sau?.ly_do || ''}`
  return head
}

/* invitations (account-invites-reset) */
const inv = reactive({ email: '', role: 'architect', ho_ten: '', error: '' })
async function saveName(u, v) {
  note.value = ''
  try { const r = await setUserName(u.id, v); u.ho_ten = r.ho_ten; note.value = `Đã lưu họ tên của ${u.email}.` }
  catch (e) { note.value = 'Chưa lưu được: ' + e.message }
}
const link = ref(null) // shown only when email is not configured: the admin passes the link on
const sentNote = (r, verb) => {
  link.value = r.link ? { email: r.user.email, url: r.link, copied: false } : null
  note.value = r.gui_email ? `Đã ${verb} lời mời tới ${r.user.email}.` : `Đã tạo lời mời cho ${r.user.email}, sao chép liên kết bên trên.`
}
async function invite() {
  inv.error = ''; note.value = ''
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(inv.email)) { inv.error = 'Nhập một địa chỉ email hợp lệ.'; return }
  busy.value = true
  try {
    sentNote(await inviteUser(inv.email, inv.role, inv.ho_ten), 'gửi')
    inv.email = ''; inv.ho_ten = ''
    await load()
  } catch (e) { inv.error = typeof e.detail === 'string' ? e.detail : e.message } finally { busy.value = false }
}
async function resend(u) {
  busy.value = true; error.value = ''
  try { sentNote(await resendInvite(u.id), 'gửi lại'); await load() } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function cancel(u) {
  if (!window.confirm(`Huỷ lời mời của ${u.email}? Liên kết sẽ không dùng được nữa.`)) return
  busy.value = true; error.value = ''
  try {
    await cancelInvite(u.id); link.value = null
    await load(); note.value = `Đã huỷ lời mời của ${u.email}.`
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function copyLink() {
  try { await navigator.clipboard.writeText(link.value.url); link.value.copied = true } catch { /* the field is selectable */ }
}

async function load() {
  loading.value = true
  try {
    const r = await listUsers({ ...(q.value.trim() ? { q: q.value.trim() } : {}), ...(roleFilter.value ? { role: roleFilter.value } : {}),
      ...(state.value ? { khoa: state.value } : {}) })
    items.value = r.items
    log.value = r.gan_day
    error.value = ''
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
let timer = null
function reloadSoon() { clearTimeout(timer); timer = setTimeout(load, 250) }

const message = e => (typeof e.detail === 'string' ? e.detail : Array.isArray(e.detail) ? e.detail.map(d => d.msg).join('; ') : e.message)

/* role: the select changes only after the confirmation; cancelling puts the old value back and focus on the select */
function askRole(u, e) {
  dlgError.value = ''
  pendingRole.value = { u, to: e.target.value, select: e.target }
  opener = e.target
  nextTick(() => roleEl.value.showModal())
}
function onRoleClose() {
  const p = pendingRole.value
  if (p && p.select.value !== p.u.role) p.select.value = p.u.role // cancelled (or failed): show the real role again
  pendingRole.value = null
  if (opener?.isConnected) opener.focus()
  opener = null
}
async function confirmRole() {
  const { u, to } = pendingRole.value
  busy.value = true
  try {
    await setUserRole(u.id, to)
    note.value = `Đã đổi vai trò của ${u.email} sang «${ROLE_VI[to]}».`
    u.role = to
    roleEl.value.close()
    await load()
  } catch (e) { dlgError.value = message(e) }
  finally { busy.value = false }
}

function askLock(u, e) {
  dlgError.value = ''; reason.value = ''
  locking.value = u
  opener = e.currentTarget
  nextTick(() => { lockEl.value.showModal(); document.getElementById('us-reason')?.focus() })
}
function onLockClose() { locking.value = null; if (opener?.isConnected) opener.focus(); opener = null }
async function confirmLock() {
  const text = reason.value.trim()
  if (text.length < 3) { dlgError.value = 'Lý do cần ít nhất 3 ký tự.'; return }
  busy.value = true
  try {
    await lockUser(locking.value.id, text)
    note.value = `Đã khoá ${locking.value.email}.`
    lockEl.value.close()
    await load()
  } catch (e) { dlgError.value = message(e) }
  finally { busy.value = false }
}

async function unlock(u) {
  busy.value = true; error.value = ''
  try { await unlockUser(u.id); note.value = `Đã mở khoá ${u.email}. Người đó cần đăng nhập lại.`; await load() }
  catch (e) { error.value = message(e) }
  finally { busy.value = false }
}

onMounted(load)
</script>

<style scoped>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap }
.us-page { padding-bottom: clamp(48px, 7vw, 96px) }
.us-bar { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px }
.us-search { flex: 1 1 240px }
.us-role { flex: 0 1 200px }
.us-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 }
.us-note { margin: 0 0 12px; font-size: 14px; color: var(--ink) }

.us-list { list-style: none; margin: 0; padding: 0 }
.us-item { display: grid; grid-template-columns: 1fr; gap: 8px; padding: 14px 0; border-top: 1px solid var(--line-soft) }
@media (min-width: 760px) {
  .us-item { grid-template-columns: minmax(220px, 2fr) minmax(160px, 1fr) minmax(140px, 1fr) auto; align-items: center; gap: 6px 18px }
  .us-why { grid-column: 1 / -1 }
}
.us-item.is-locked .us-email { color: var(--dim) }
.us-who { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px; min-width: 0 }
.us-email { color: var(--ink); font-weight: 500; overflow-wrap: anywhere }
.us-tags { display: inline-flex; flex-wrap: wrap; gap: 6px }
.us-tag { font-size: 12px; border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; color: var(--dim) }
.us-tag.is-me { color: var(--accent); border-color: currentColor }
.us-tag.is-active { color: var(--success); border-color: currentColor }
.us-tag.is-locked-tag { color: var(--danger); border-color: currentColor }
.us-tag.is-pending { color: var(--warn); border-color: currentColor }
.us-invite { margin-top: 24px; display: grid; gap: 10px; padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md);
  background: var(--panel) }
.us-invite .h-4 { margin: 0 }
.us-inv-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center }
.us-inv-email { flex: 1 1 240px; min-width: 0 }
.us-link { margin-top: 12px; display: grid; gap: 8px; padding: 12px 14px; border: 1px dashed var(--accent); border-radius: var(--radius-md) }
.us-since { color: var(--dim); width: 100% }
.us-role-cell select { width: 100% }
.us-state { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px }
.us-reason { color: var(--dim); overflow-wrap: anywhere }
.us-danger { color: var(--danger) }
.us-why { margin: 0; color: var(--dim) }

.us-log { margin-top: 32px }
.us-log ol { list-style: none; margin: 10px 0 0; padding: 0; display: grid; gap: 6px }
.us-log li { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 13px; color: var(--ink); overflow-wrap: anywhere }
.us-dim { color: var(--dim) }
.us-dialog { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--page); color: var(--ink);
             padding: 20px; width: min(480px, calc(100vw - 32px)) }
.us-dialog::backdrop { background: rgba(0, 0, 0, 0.55) }
.us-dialog textarea { width: 100% }
.us-name { max-width: 220px; min-height: 34px; padding: 4px 8px; font-size: 14px } /* admin-tools */
</style>
