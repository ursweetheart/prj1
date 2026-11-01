<template>
  <HeroSlideshow />

  <ProjectGrid />

  <!-- CTA -->
  <section class="sec sec-line wrap">
    <div class="panel" style="display:grid; gap:18px; max-width:66ch">
      <h2 class="h-2">Bạn đang có một không gian cần thiết kế?</h2>
      <p class="body" style="margin:0">
        Để lại thông tin, kiến trúc sư D3 Studio sẽ liên hệ với bạn.
      </p>
      <div class="row wrapx g10">
        <router-link class="btn btn-primary" to="/lien-he">Gửi yêu cầu</router-link>
        <router-link class="btn btn-secondary" to="/cong-trinh">Xem các không gian</router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import HeroSlideshow from '@/components/HeroSlideshow.vue'
import ProjectGrid from '@/components/ProjectGrid.vue'
</script>
