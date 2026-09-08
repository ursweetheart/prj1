<template>
  <SiteNav :current="currentNav" />
  <router-view />
  <SiteFoot />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SiteNav from '@/components/SiteNav.vue'
import SiteFoot from '@/components/SiteFoot.vue'

const route = useRoute()
const currentNav = computed(() => {
  if (route.path === '/') return 'trang-chu'
  if (route.path === '/cong-trinh') return 'cong-trinh'
  if (route.path === '/dich-vu') return 'dich-vu'
  if (route.path === '/ve-chung-toi') return 've-chung-toi'
  if (route.path === '/lien-he') return 'lien-he'
  return ''
})
</script>
