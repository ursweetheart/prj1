<template>
  <section class="wr" aria-labelledby="wr-h">
    <h2 id="wr-h" class="wr-h">Báo cáo tuần <span class="wr-note">gửi tự động thứ Hai từ 8:00</span></h2>

    <p v-if="error" class="small" style="color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!rows" class="small">Đang tải…</p>
    <p v-else-if="!rows.length" class="small">Chưa gửi báo cáo nào.</p>
    <table v-else class="wr-table">
      <thead>
        <tr><th scope="col">Tuần</th><th scope="col">Gửi lúc</th><th scope="col">Người nhận</th><th scope="col">Lỗi</th>
          <th scope="col">Kết quả</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.tuan_bat_dau">
          <td data-k="Tuần" class="num">{{ weekText(r.tuan_bat_dau) }}</td>
          <td data-k="Gửi lúc" class="num">{{ timeText(r.gui_luc) }}</td>
          <td data-k="Người nhận" class="num">{{ r.so_nguoi_nhan }}</td>
          <td data-k="Lỗi" class="num">{{ r.so_loi }}</td>
          <td data-k="Kết quả"><span class="wr-badge" :class="'is-' + r.ket_qua">{{ RESULT[r.ket_qua] || r.ket_qua }}</span></td>
        </tr>
      </tbody>
    </table>

    <div class="row g10 wr-actions">
      <button type="button" class="btn btn-secondary" :aria-expanded="String(!!preview)" aria-controls="wr-preview"
              :disabled="busy === 'preview'" @click="togglePreview">{{ preview ? 'Ẩn bản xem trước' : 'Xem trước' }}</button>
      <button type="button" class="btn btn-secondary" :disabled="busy === 'test'" @click="sendTest">
        {{ busy === 'test' ? 'Đang gửi…' : 'Gửi thử cho tôi' }}</button>
    </div>
    <p v-if="msg" class="small" role="status" style="margin-top:10px">{{ msg }}</p>

    <div v-if="preview" id="wr-preview" class="wr-preview">
      <p class="small">Gửi tới {{ preview.nguoi_nhan }} người · <strong>{{ preview.tieu_de }}</strong></p>
      <pre>{{ preview.noi_dung }}</pre>
    </div>
  </section>
</template>

<script setup>
/* Báo cáo tuần (UC23; seq-18) cho KTS trưởng và admin: lịch sử gửi, xem trước, gửi thử cho chính mình. */
import { ref } from 'vue'
import { listWeeklyReports, previewWeeklyReport, testWeeklyReport } from '@/api'

const RESULT = { da_gui: 'Đã gửi', chi_ghi_log: 'Chỉ ghi log', loi_mot_phan: 'Lỗi một phần', loi: 'Lỗi', dang_gui: 'Đang gửi / dừng giữa chừng' }

const rows = ref(null)
const error = ref('')
const preview = ref(null)
const busy = ref('')
const msg = ref('')

const pad = n => String(n).padStart(2, '0')
const dm = d => pad(d.getDate()) + '/' + pad(d.getMonth() + 1)
function weekText(iso) { // the Monday it starts, through Sunday
  const start = new Date(iso + 'T00:00:00')
  const end = new Date(start); end.setDate(end.getDate() + 6)
  return dm(start) + ' – ' + dm(end) + '/' + end.getFullYear()
}
const timeText = iso => { const d = new Date(iso); return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ' ' + dm(d) }

listWeeklyReports().then(r => { rows.value = r }, e => { error.value = e.message })

async function togglePreview() {
  if (preview.value) { preview.value = null; return }
  busy.value = 'preview'; msg.value = ''
  try { preview.value = await previewWeeklyReport() } catch (e) { msg.value = e.message } finally { busy.value = '' }
}

async function sendTest() {
  busy.value = 'test'; msg.value = ''
  try {
    const r = await testWeeklyReport()
    msg.value = 'Đã gửi bản thử tới ' + r.gui_toi + '.'
  } catch (e) {
    msg.value = e.status === 409 ? 'Chưa cấu hình email (D3_SMTP_HOST), nên chưa gửi thử được. Báo cáo hằng tuần vẫn được ghi vào log.' : e.message
  } finally { busy.value = '' }
}
</script>

<style scoped>
.wr { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel); padding: 16px 18px; margin-top: 16px; min-width: 0 }
.wr-h { margin: 0 0 12px; font-size: 16px; font-weight: 500; color: var(--ink) }
.wr-note { font-size: 12px; font-weight: 400; color: var(--faint); margin-left: 6px }
.wr-table { width: 100%; border-collapse: collapse; font-size: 14px; color: var(--ink-2) }
.wr-table th { text-align: left; font-weight: 400; font-size: 12px; color: var(--faint); padding: 6px 8px; border-bottom: 1px solid var(--line) }
.wr-table td { padding: 8px; border-bottom: 1px solid var(--line-soft) }
.wr-badge { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--dim); white-space: nowrap }
.wr-badge.is-da_gui { border-color: var(--success); color: var(--success) }
.wr-badge.is-loi, .wr-badge.is-loi_mot_phan, .wr-badge.is-dang_gui { border-color: var(--danger); color: var(--danger) }
.wr-actions { margin-top: 14px; flex-wrap: wrap }
.wr-preview { margin-top: 14px; border-top: 1px solid var(--line-soft); padding-top: 12px; min-width: 0 }
.wr-preview pre { margin: 8px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; line-height: 1.55;
                  color: var(--ink-2); background: var(--page); border-radius: var(--radius-sm); padding: 12px 14px }

@media (max-width: 600px) {
  .wr-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0) }
  .wr-table, .wr-table tbody, .wr-table tr, .wr-table td { display: block }
  .wr-table tr { padding: 8px 0; border-bottom: 1px solid var(--line-soft) }
  .wr-table td { display: flex; justify-content: space-between; gap: 12px; padding: 3px 0; border: 0 }
  .wr-table td::before { content: attr(data-k); color: var(--faint); font-size: 12px }
}
</style>
