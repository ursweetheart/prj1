<template>
  <SiteNav :current="currentNav" />
  <router-view />
  <SiteFoot />
  <ChatWidget />
  <ConsentBanner />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SiteNav from '@/components/SiteNav.vue'
import SiteFoot from '@/components/SiteFoot.vue'
import ChatWidget from '@/components/ChatWidget.vue'
import ConsentBanner from '@/components/ConsentBanner.vue'

const route = useRoute()
const currentNav = computed(() => {
  if (route.path === '/') return 'trang-chu'
  if (route.path === '/du-an' || route.path.startsWith('/du-an/')) return 'du-an'
  if (route.path === '/khong-gian' || route.path.startsWith('/khong-gian/')) return 'khong-gian'
  if (route.path === '/dich-vu') return 'dich-vu'
  if (route.path === '/ve-chung-toi') return 've-chung-toi'
  if (route.path === '/lien-he') return 'lien-he'
  return ''
})
</script>
