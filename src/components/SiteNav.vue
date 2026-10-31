<template>
  <header class="nav nav-transparent">
    <div class="nav-in" style="padding-inline: clamp(24px, 4vw, 64px);">
      <div class="nav-left">
        <router-link class="brand" to="/" aria-label="D3 Studio · trang chủ">
          <BrandMark /><span class="brand-word">D3 Studio</span>
        </router-link>
      </div>

      <div class="nav-center">
        <nav class="nav-links" aria-label="Điều hướng chính">
          <router-link v-for="l in links" :key="l.key" :to="l.to"
             :class="{ 'is-active': current === l.key || ($route && $route.path === l.to) }"
             :aria-current="(current === l.key || ($route && $route.path === l.to)) ? 'page' : undefined">{{ l.label }}</router-link>
        </nav>
      </div>

      <div class="nav-right">
        <div class="nav-account">
          <router-link v-for="l in roleLinks" :key="l.to" :to="l.to">{{ l.label }}</router-link>
          <button v-if="session.user" type="button" @click="signOut">Đăng xuất</button>
          <router-link v-else to="/dang-nhap">Đăng nhập</router-link>
        </div>

        <div class="lang-switch" aria-label="Chuyển đổi ngôn ngữ">
          <button type="button" :class="{ active: currentLang === 'VI' }" @click="currentLang = 'VI'">Vi</button>
          <span class="sep">|</span>
          <button type="button" :class="{ active: currentLang === 'EN' }" @click="currentLang = 'EN'">En</button>
        </div>
        <button class="nav-burger" type="button" :aria-expanded="String(open)"
                aria-label="Mở menu" @click="open = !open"><span></span></button>
      </div>
    </div>
    
    <div class="nav-sheet" v-if="open">
      <router-link v-for="l in links" :key="l.key" :to="l.to" @click="open = false"
                   :class="{ 'is-active': current === l.key || ($route && $route.path === l.to) }">{{ l.label }}</router-link>
      <router-link v-for="l in roleLinks" :key="l.to" :to="l.to" @click="open = false">{{ l.label }}</router-link>
      <button v-if="session.user" type="button" @click="signOut(); open = false">Đăng xuất</button>
      <router-link v-else to="/dang-nhap" @click="open = false">Đăng nhập</router-link>
      <div class="nav-sheet-lang">
        <button type="button" :class="{ active: currentLang === 'VI' }" @click="currentLang = 'VI'">Vi</button>
        <span class="sep">|</span>
        <button type="button" :class="{ active: currentLang === 'EN' }" @click="currentLang = 'EN'">En</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EDITORS, SALES, hasRole, logout, session } from '@/api'
import BrandMark from './BrandMark.vue'

defineProps({
  current: { type: String, default: '' }
})

const route = useRoute()
const router = useRouter()
const open = ref(false)
const currentLang = ref('VI')

const links = [
  { to: '/cong-trinh',  label: 'Dự án',   key: 'cong-trinh' },
  { to: '/ve-chung-toi', label: 'Về chúng tôi', key: 've-chung-toi' },
  { to: '/lien-he',     label: 'Liên hệ',    key: 'lien-he' }
]

const roleLinks = computed(() => [
  hasRole(EDITORS) && { to: '/quan-tri', label: 'Duyệt' },
  hasRole(SALES) && { to: '/khach-hang', label: 'Khách hàng' }
].filter(Boolean))

function signOut() { logout(); router.push('/') }
</script>
