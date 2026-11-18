<template>
  <aside v-if="open" class="consent" role="region" aria-label="Đồng ý thu thập dữ liệu" @keydown.esc="answered && close()">
    <p class="small" style="margin:0">
      D3 Studio muốn ghi nhận những không gian bạn xem, ẩn danh và không gắn với tài khoản, để hiểu điều khách quan tâm,
      cải thiện bộ lọc và gợi ý không gian hợp với bạn. Không đồng ý thì chúng tôi chỉ đếm tổng lượt xem trong ngày.
    </p>

    <!-- act-7: Đồng ý / Từ chối / Tùy chỉnh -->
    <div v-if="!custom" class="row g10" style="margin-top:12px;flex-wrap:wrap">
      <button ref="first" class="btn btn-primary" type="button" @click="choose('yes')">Đồng ý</button>
      <button class="btn btn-secondary" type="button" @click="choose('no')">Từ chối</button>
      <button class="btn btn-ghost" type="button" :aria-expanded="String(custom)" @click="openCustom">Tùy chỉnh</button>
    </div>

    <div v-else class="stack" style="margin-top:12px;gap:10px">
      <div class="sw-row">
        <span :id="'sw-pt'" class="sw-text"><strong>Phân tích</strong><br><span class="small">Ghi nhận những gì bạn xem, ẩn danh, để hiểu xu hướng.</span></span>
        <button ref="first" class="sw" type="button" role="switch" :aria-checked="String(analytics)" aria-labelledby="sw-pt"
                @click="analytics = !analytics; if (!analytics) personal = false"></button>
      </div>
      <div class="sw-row">
        <span :id="'sw-cn'" class="sw-text"><strong>Cá nhân hóa</strong><br>
          <span class="small">Ưu tiên gợi ý theo những gì bạn đã xem{{ analytics ? '' : ' (cần bật Phân tích)' }}.</span></span>
        <button class="sw" type="button" role="switch" :aria-checked="String(personal)" aria-labelledby="sw-cn"
                :disabled="!analytics" @click="personal = !personal"></button>
      </div>
      <div class="row g10" style="flex-wrap:wrap">
        <button class="btn btn-primary" type="button" @click="choose(analytics ? (personal ? 'yes' : 'phan_tich') : 'no')">Lưu lựa chọn</button>
        <button v-if="answered" class="btn btn-ghost" type="button" @click="close">Đóng</button>
      </div>

      <!-- act-7 "Gửi yêu cầu xóa dữ liệu cá nhân" -->
      <div v-if="answered" class="forget">
        <button v-if="!confirming" class="btn btn-ghost" type="button" @click="confirming = true">Xóa dữ liệu của tôi</button>
        <p v-else class="small" style="margin:0">
          Xóa mọi phiên và sự kiện đã ghi nhận từ trình duyệt này?
          <button class="btn btn-secondary" type="button" :disabled="busy" @click="forget">Xóa</button>
          <button class="btn btn-ghost" type="button" @click="confirming = false">Hủy</button>
        </p>
      </div>
    </div>
    <p v-if="note" class="small" role="status" style="margin:10px 0 0">{{ note }}</p>
  </aside>
</template>

<script setup>
/* act-7 (tracking-pipeline): three choices on the first visit, Tùy chỉnh with two switches (personalisation needs
   analytics), the footer's "Cài đặt dữ liệu" reopens it with the current answer, and the visitor can delete what was
   collected from this browser. */
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { consent, forgetMe } from '@/api'

const answered = ref(!!consent.get())
const open = ref(!answered.value)
const custom = ref(false)
const analytics = ref(consent.analytics())
const personal = ref(consent.personal())
const confirming = ref(false)
const busy = ref(false)
const note = ref('')
const first = ref(null)

function choose(v) {
  consent.set(v)
  answered.value = true
  note.value = ''
  close()
}
function close() { open.value = false; custom.value = false; confirming.value = false }
async function openCustom() {
  custom.value = true
  await nextTick()
  first.value?.focus()
}
async function reopen() { // footer: the current answer is selected
  analytics.value = consent.analytics(); personal.value = consent.personal()
  note.value = ''; confirming.value = false
  open.value = true
  await openCustom()
}
async function forget() {
  busy.value = true
  try {
    const r = await forgetMe()
    note.value = r.so_phien ? `Đã xóa ${r.so_phien} phiên, ${r.so_su_kien} sự kiện.` : 'Không có dữ liệu nào được lưu.'
    confirming.value = false
  } catch (e) { note.value = 'Chưa xóa được: ' + e.message }
  finally { busy.value = false }
}
onMounted(() => window.addEventListener('d3-consent-open', reopen))
onBeforeUnmount(() => window.removeEventListener('d3-consent-open', reopen))
</script>

<style scoped>
/* bottom-left: the chat button owns the bottom-right corner */
.consent { position: fixed; left: 16px; bottom: 16px; z-index: 39; max-width: min(420px, calc(100vw - 32px));
           padding: 16px; background: var(--panel); color: var(--ink); border: 1px solid var(--line);
           border-radius: var(--radius-md); box-shadow: var(--elev-raised) }
@media (max-width: 640px) { .consent { bottom: 84px } } /* above the chat button on phones */
.sw-row { display: flex; align-items: center; justify-content: space-between; gap: 12px }
.sw-text { flex: 1 }
.sw { flex: none; width: 44px; height: 26px; border-radius: 13px; border: 1px solid var(--line); background: var(--line-soft);
      position: relative; cursor: pointer; padding: 0 }
.sw::after { content: ''; position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%;
             background: var(--dim); transition: transform .15s }
.sw[aria-checked="true"] { background: var(--accent); border-color: var(--accent) }
.sw[aria-checked="true"]::after { transform: translateX(18px); background: var(--page) }
.sw:disabled { opacity: .45; cursor: not-allowed }
.sw:focus-visible { box-shadow: var(--focus-ring); outline: none }
.forget { border-top: 1px solid var(--line); padding-top: 10px }
</style>
