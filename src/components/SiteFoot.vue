<template>
  <footer class="foot">
    <div class="wrap wrap-wide">
      <div class="foot-grid">
        <div>
          <router-link class="brand" to="/"><BrandMark /><span class="brand-word">D3 Studio</span></router-link>
          <p class="small" style="margin-top:14px; max-width:38ch">
            Tư vấn thiết kế kiến trúc, nội thất cao cấp và diễn họa 3D tại Hà Nội.
          </p>
        </div>
        <div>
          <h5>Khám phá</h5>
          <router-link to="/du-an">Dự án</router-link>
          <router-link to="/du-an#loai=nha-o">Nhà ở</router-link>
          <router-link to="/du-an#loai=thuong-mai">Thương mại</router-link>
          <router-link to="/dich-vu">Dịch vụ và quy trình</router-link>
          <router-link to="/trac-nghiem">Trắc nghiệm phong cách</router-link>
          <router-link to="/ve-chung-toi">Về chúng tôi</router-link>
        </div>
        <div>
          <h5>Liên hệ</h5>
          <router-link to="/lien-he">Gửi yêu cầu tư vấn</router-link>
          <router-link to="/lien-he#zalo">Nhắn Zalo</router-link>
          <router-link to="/lien-he#ban-do">Địa chỉ và bản đồ</router-link>
        </div>
      </div>
      <div class="foot-base">
        <span>© {{ new Date().getFullYear() }} D3 Studio</span>
        <span>Kiến trúc · Nội thất · Diễn họa 3D</span>
        <button class="foot-link" type="button" @click="openConsent">Cài đặt dữ liệu</button>
      </div>
    </div>
  </footer>
</template>

<script setup>
import BrandMark from './BrandMark.vue'
import { openConsent } from '@/api' // act-7: change the data choice from the footer
</script>

<style scoped>
.foot-link { background: none; border: 0; padding: 0; font: inherit; color: inherit; cursor: pointer; text-decoration: underline;
             text-underline-offset: 3px }
.foot-link:hover { color: var(--ink) }
.foot-link:focus-visible { box-shadow: var(--focus-ring); outline: none; border-radius: 2px }
</style>
