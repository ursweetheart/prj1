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
      <div class="cta-links">
        <router-link class="cta-link glow-hover" to="/lien-he">
          Gửi yêu cầu <span class="arrow" aria-hidden="true">→</span>
        </router-link>
        <router-link class="cta-link glow-hover" to="/du-an">
          Xem tất cả dự án <span class="arrow" aria-hidden="true">→</span>
        </router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import HeroSlideshow from '@/components/HeroSlideshow.vue'
import ProjectGrid from '@/components/ProjectGrid.vue'
import SpaceSearchBand from '@/components/SpaceSearchBand.vue'
</script>
