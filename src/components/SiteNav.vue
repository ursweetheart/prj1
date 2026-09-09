<template>
  <header class="nav nav-transparent">
    <div class="wrap wrap-wide">
      <div class="nav-in">
        <router-link class="brand" to="/" aria-label="D3 Studio · trang chủ">
          <BrandMark /><span class="brand-word">D3 Studio</span>
        </router-link>

        <div class="nav-right">
          <nav class="nav-links" aria-label="Điều hướng chính">
            <router-link v-for="l in links" :key="l.key" :to="l.to"
               :class="{ 'is-active': current === l.key || ($route && $route.path === l.to) }"
               :aria-current="(current === l.key || ($route && $route.path === l.to)) ? 'page' : undefined">{{ l.label }}</router-link>
          </nav>

          <div class="lang-switch" aria-label="Chuyển đổi ngôn ngữ">
            <button type="button" :class="{ active: currentLang === 'VI' }" @click="currentLang = 'VI'">Vi</button>
            <span class="sep">|</span>
            <button type="button" :class="{ active: currentLang === 'EN' }" @click="currentLang = 'EN'">En</button>
          </div>
        </div>

        <button class="nav-burger" type="button" :aria-expanded="String(open)"
                aria-label="Mở menu" @click="open = !open"><span></span></button>
      </div>
    </div>
    
    <div class="nav-sheet" v-if="open">
      <router-link v-for="l in links" :key="l.key" :to="l.to" @click="open = false"
                   :class="{ 'is-active': current === l.key || ($route && $route.path === l.to) }">{{ l.label }}</router-link>
      <div class="nav-sheet-lang">
        <button type="button" :class="{ active: currentLang === 'VI' }" @click="currentLang = 'VI'">Vi</button>
        <span class="sep">|</span>
        <button type="button" :class="{ active: currentLang === 'EN' }" @click="currentLang = 'EN'">En</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import BrandMark from './BrandMark.vue'

defineProps({
  current: { type: String, default: '' }
})

const route = useRoute()
const open = ref(false)
const currentLang = ref('VI')

const links = [
  { to: '/cong-trinh',  label: 'Dự án',   key: 'cong-trinh' },
  { to: '/dich-vu',     label: 'Dịch vụ',    key: 'dich-vu' },
  { to: '/ve-chung-toi', label: 'Về chúng tôi', key: 've-chung-toi' },
  { to: '/lien-he',     label: 'Liên hệ',    key: 'lien-he' }
]
</script>
