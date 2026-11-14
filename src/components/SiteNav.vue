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
          <router-link v-if="ai.state === 'on'" to="/bo-suu-tap" class="nav-saved"
                       :aria-label="'Bộ sưu tập, ' + savedCount + ' ảnh'">Bộ sưu tập<span v-if="savedCount" class="num"> ({{ savedCount }})</span></router-link>
          <!-- staff links: one inline, two or more grouped so the header never runs out of room -->
          <router-link v-if="roleLinks.length === 1" :to="roleLinks[0].to">{{ roleLinks[0].label }}</router-link>
          <div v-else-if="roleLinks.length" ref="menuEl" class="nav-menu" @keydown.esc.stop="closeMenu(true)">
            <button ref="menuBtn" type="button" class="nav-menu-btn" :class="{ 'is-here': onStaffPage }"
                    aria-haspopup="true" :aria-expanded="String(menuOpen)" aria-controls="nav-staff"
                    @click="menuOpen = !menuOpen">Quản trị <span class="nav-caret" aria-hidden="true">▾</span></button>
            <ul v-show="menuOpen" id="nav-staff" class="nav-menu-list">
              <li v-for="l in roleLinks" :key="l.to">
                <router-link :to="l.to" :aria-current="route.path === l.to ? 'page' : undefined"
                             @click="closeMenu(false)">{{ l.label }}</router-link>
              </li>
            </ul>
          </div>
          <button v-if="session.user" type="button" @click="signOut">Đăng xuất</button>
          <router-link v-else to="/dang-nhap">Đăng nhập</router-link>
        </div>

        <div class="lang-switch" aria-label="Chuyển đổi ngôn ngữ">
          <button type="button" :class="{ active: currentLang === 'VI' }" @click="currentLang = 'VI'">Vi</button>
          <span class="sep">|</span>
          <button type="button" :class="{ active: currentLang === 'EN' }" @click="currentLang = 'EN'">En</button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APPROVERS, EDITORS, SALES, hasRole, logout, session } from '@/api'
import { ai, aiAvailable } from '@/lib/projectSpaces'
import { collection } from '@/lib/collection'
import BrandMark from './BrandMark.vue'

defineProps({
  current: { type: String, default: '' }
})

const route = useRoute()
const router = useRouter()
const currentLang = ref('VI')

// "Không gian" (tìm không gian tương tự bằng AI) chỉ hiện khi backend trả lời
aiAvailable()
const links = computed(() => [
  { to: '/du-an',       label: 'Dự án',   key: 'du-an' },
  ai.state === 'on' && { to: '/khong-gian', label: 'Không gian', key: 'khong-gian' },
  { to: '/ve-chung-toi', label: 'Về chúng tôi', key: 've-chung-toi' },
  { to: '/lien-he',     label: 'Liên hệ',    key: 'lien-he' }
].filter(Boolean))

const savedCount = computed(() => collection.items.length)

const roleLinks = computed(() => [
  hasRole(EDITORS) && { to: '/quan-tri', label: 'Duyệt' },
  hasRole(APPROVERS) && { to: '/quan-tri/phan-loai', label: 'Phân loại' },
  hasRole(APPROVERS) && { to: '/quan-tri/don-gia', label: 'Đơn giá' },
  hasRole(SALES) && { to: '/khach-hang', label: 'Khách hàng' },
  hasRole(SALES) && { to: '/quan-tri/xu-huong', label: 'Xu hướng' }
].filter(Boolean))

const onStaffPage = computed(() => roleLinks.value.some(l => route.path === l.to))

/* "Quản trị" menu: a disclosure button; closes on Esc (focus back to the button), outside click or navigation */
const menuOpen = ref(false)
const menuEl = ref(null)
const menuBtn = ref(null)
function closeMenu(refocus) {
  if (!menuOpen.value) return
  menuOpen.value = false
  if (refocus) menuBtn.value?.focus()
}
function onOutside(e) { if (menuOpen.value && menuEl.value && !menuEl.value.contains(e.target)) closeMenu(false) }
watch(() => route.fullPath, () => closeMenu(false))
onMounted(() => document.addEventListener('pointerdown', onOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))

function signOut() { logout(); router.push('/') }
</script>
