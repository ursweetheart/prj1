<template>
  <HeroSlideshow />

  <ProjectGrid />

  <SpaceSearchBand />

  <!-- CTA -->
  <section class="cta wrap" aria-labelledby="cta-title">
    <div class="cta-in">
      <div>
        <p class="cta-eyebrow">Liên hệ</p>
        <h2 id="cta-title" class="cta-title">Ý tưởng về một không gian cá nhân hoá, hãy để lại thông tin</h2>
        <p class="cta-text">Kiến trúc sư D3 Studio sẽ liên hệ với bạn.</p>
      </div>
      <nav class="link-list" aria-label="Liên hệ">
        <router-link class="ll-item" to="/lien-he">
          <span class="ll-n" aria-hidden="true">01</span><span class="ll-label">Gửi yêu cầu</span><span class="ll-arrow" aria-hidden="true">→</span>
        </router-link>
        <router-link class="ll-item" to="/du-an">
          <span class="ll-n" aria-hidden="true">02</span><span class="ll-label">Xem tất cả dự án</span><span class="ll-arrow" aria-hidden="true">→</span>
        </router-link>
      </nav>
    </div>
  </section>
</template>

<script setup>
import HeroSlideshow from '@/components/HeroSlideshow.vue'
import ProjectGrid from '@/components/ProjectGrid.vue'
import SpaceSearchBand from '@/components/SpaceSearchBand.vue'
</script>
