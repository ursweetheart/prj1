<template>
  <aside v-if="!answered" class="consent" role="region" aria-label="Đồng ý thu thập dữ liệu">
    <p class="small" style="margin:0">
      D3 Studio muốn ghi nhận những không gian bạn xem, ẩn danh và không gắn với tài khoản, để hiểu điều khách quan tâm
      và cải thiện bộ lọc. Không đồng ý thì chúng tôi chỉ đếm tổng lượt xem trong ngày.
    </p>
    <div class="row g10" style="margin-top:12px">
      <button class="btn btn-primary" type="button" @click="choose('yes')">Đồng ý</button>
      <button class="btn btn-secondary" type="button" @click="choose('no')">Không đồng ý</button>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { consent } from '@/api'

const answered = ref(!!consent.get())
function choose(v) { consent.set(v); answered.value = true }
</script>

<style scoped>
/* bottom-left: the chat button owns the bottom-right corner */
.consent { position: fixed; left: 16px; bottom: 16px; z-index: 39; max-width: min(420px, calc(100vw - 32px));
           padding: 16px; background: var(--panel); color: var(--ink); border: 1px solid var(--line);
           border-radius: var(--radius-md); box-shadow: var(--elev-raised) }
@media (max-width: 640px) { .consent { bottom: 84px } } /* above the chat button on phones */
</style>
