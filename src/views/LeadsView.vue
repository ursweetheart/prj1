<template>
  <main class="wrap wrap-wide" style="padding-block:clamp(28px,4vw,56px)">
    <p class="eyebrow">Kinh doanh</p>
    <h1 class="h-2" style="margin-top:10px">Khách để lại thông tin</h1>
    <p class="lead" style="margin-top:10px">Tạo từ trợ lý chat: hỏi giá, xin hẹn, hoặc câu hỏi trợ lý chưa trả lời được.</p>

    <p v-if="error" class="small" style="margin-top:16px;color:var(--danger)" role="alert">{{ error }}</p>
    <p v-else-if="!leads.length" class="small" style="margin-top:20px">{{ loading ? 'Đang tải…' : 'Chưa có khách nào.' }}</p>

    <ul class="stack" style="margin-top:20px;gap:14px;list-style:none;padding:0">
      <li v-for="l in leads" :key="l.id" class="form-ok" style="display:block">
        <div class="row g10" style="flex-wrap:wrap">
          <span class="chip chip-static">{{ INTENT_VI[l.intent] || l.intent }}</span>
          <strong>{{ l.contact || 'Chưa có liên hệ' }}</strong>
          <span class="small">{{ new Date(l.created_at).toLocaleString('vi-VN') }}</span>
        </div>
        <p class="small" style="margin-top:10px">{{ summary(l.request) }}</p>
        <details style="margin-top:10px">
          <summary class="small">Hội thoại ({{ (l.conversation || []).length }})</summary>
          <p v-for="(m, i) in l.conversation" :key="i" class="small" style="margin-top:6px">
            <strong>{{ m.role === 'user' ? 'Khách' : 'Trợ lý' }}:</strong> {{ m.content }}
          </p>
        </details>
      </li>
    </ul>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listLeads, spaceLabel } from '@/api'

const INTENT_VI = { price: 'Hỏi giá', appointment: 'Xin hẹn', handoff: 'Chuyển kiến trúc sư' }
const PROJECT_VI = { can_ho: 'Căn hộ', biet_thu: 'Biệt thự', nha_pho: 'Nhà phố', van_phong: 'Văn phòng', thuong_mai: 'Thương mại' }
const leads = ref([])
const loading = ref(true)
const error = ref('')

// what the assistant understood from the question: only show the fields it found
function summary(req = {}) {
  return [PROJECT_VI[req.project_type], req.space_type && spaceLabel(req.space_type), req.design_style,
          req.area_m2 && req.area_m2 + ' m²'].filter(Boolean).join(' · ') || 'Chưa nhận diện được yêu cầu cụ thể'
}

onMounted(async () => {
  try { leads.value = await listLeads() } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>
