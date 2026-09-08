<template>
  <footer class="foot">
    <div class="wrap wrap-wide">
      <div class="foot-grid">
        <div>
          <router-link class="brand" to="/"><BrandMark /><span class="brand-word">D3 Studio</span></router-link>
          <p class="small" style="margin-top:14px; max-width:38ch">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
            tempor incididunt ut labore et dolore magna aliqua veniam.
          </p>
        </div>
        <div>
          <h5>Khám phá</h5>
          <router-link to="/cong-trinh">Công trình</router-link>
          <router-link to="/cong-trinh?loai=chung-cu">Nhà ở</router-link>
          <router-link to="/cong-trinh?loai=lounge">Thương mại</router-link>
          <router-link to="/dich-vu">Dịch vụ và quy trình</router-link>
          <router-link to="/ve-chung-toi">Về chúng tôi</router-link>
        </div>
        <div>
          <h5>Liên hệ</h5>
          <router-link to="/lien-he">Gửi yêu cầu tư vấn</router-link>
          <router-link to="/lien-he#zalo">Nhắn Zalo</router-link>
          <router-link to="/lien-he#ban-do">Địa chỉ và bản đồ</router-link>
          <p class="small" style="margin-top:10px">
            Lorem ipsum dolor sit amet — consectetur adipiscing elit tempor.
          </p>
        </div>
      </div>
      <div class="foot-base">
        <span>© {{ new Date().getFullYear() }} D3 Studio</span>
        <span>Lorem ipsum dolor sit amet D3 Studio</span>
      </div>
    </div>
  </footer>
</template>

<script setup>
import BrandMark from './BrandMark.vue'
</script>
