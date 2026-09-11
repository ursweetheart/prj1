<template>
  <img 
    :src="logoUrl" 
    alt="D3 Studio Logo" 
    class="brand-mark"
  />
</template>

<script setup>
import { computed } from 'vue'

const logoUrl = computed(() => `${import.meta.env.BASE_URL}img/logo_xoa_nen.png`)
</script>

