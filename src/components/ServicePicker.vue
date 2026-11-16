<template>
  <label class="sp" :for="id">Dịch vụ liên quan
    <select :id="id" class="txt" :value="modelValue ?? ''"
            @change="$emit('update:modelValue', $event.target.value ? Number($event.target.value) : null)">
      <option value="">Không gắn dịch vụ</option>
      <option v-for="s in services" :key="s.id" :value="s.id">{{ s.title }}{{ s.trang_thai === 'dang_dung' ? '' : ' (chưa dùng)' }}</option>
    </select>
    <span class="small">Gói dịch vụ trong kho tri thức mà món đồ thuộc về. Thẻ điểm nóng của khách vẫn chỉ hiện tên.</span>
  </label>
</template>

<script setup>
/* An item's service package (change topic-guard-sitemap-item-services): a knowledge entry of kind "service". */
defineProps({ modelValue: { type: Number, default: null }, services: { type: Array, default: () => [] }, id: { type: String, required: true } })
defineEmits(['update:modelValue'])
</script>

<style scoped>
.sp { display: grid; gap: 4px; font-size: 13px; color: var(--dim) }
.sp .txt { width: 100%; max-width: 100%; background: var(--panel); color: var(--ink); border: 1px solid var(--line);
  border-radius: var(--radius-md); padding: 8px 10px; min-height: 40px; font: inherit; color-scheme: dark }
</style>
