<template>
  <header class="nav">
    <div class="wrap wrap-wide">
      <div class="nav-in">
        <router-link class="brand" to="/" aria-label="D3 Studio · trang chủ">
          <BrandMark /><span class="brand-word">D3 Studio</span>
        </router-link>
        <nav class="nav-links" aria-label="Điều hướng chính">
          <router-link v-for="l in links" :key="l.key" :to="l.to"
             :aria-current="current === l.key ? 'page' : undefined">{{ l.label }}</router-link>
        </nav>
        <router-link class="btn btn-secondary nav-cta" to="/lien-he">
          Nhận tư vấn<span v-if="moodboard.count.value" class="num"> · đã lưu {{ moodboard.count.value }}</span>
        </router-link>
        <button class="nav-burger" type="button" :aria-expanded="String(open)"
                aria-label="Mở menu" @click="open = !open"><span></span></button>
      </div>
    </div>
    <div class="nav-sheet" v-if="open">
      <router-link v-for="l in links" :key="l.key" :to="l.to" @click="open = false">{{ l.label }}</router-link>
      <router-link class="btn btn-primary" to="/lien-he" style="margin-top:12px" @click="open = false">Nhận tư vấn</router-link>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import BrandMark from './BrandMark.vue'
import { useMoodboard } from '@/composables/useMoodboard'

defineProps({
  current: { type: String, default: '' }
})

const open = ref(false)
const moodboard = useMoodboard()
const links = [
  { to: '/cong-trinh', label: 'Công trình', key: 'cong-trinh' },
  { to: '/dich-vu',    label: 'Dịch vụ',    key: 'dich-vu' },
  { to: '/ve-chung-toi', label: 'Về chúng tôi', key: 've-chung-toi' },
  { to: '/lien-he',    label: 'Liên hệ',    key: 'lien-he' }
]
</script>
