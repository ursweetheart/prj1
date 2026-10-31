<template>
  <!-- Hero -->
  <section class="hero">
    <div class="media"><img :src="base + 'img/indochine-apartment-hero.jpg'" alt="D3 Studio - Indochine Apartment"></div>
  </section>

  <!-- Nổi bật (ẩn khi chưa có không gian nào được đăng) -->
  <section v-if="featured.length" class="sec wrap wrap-wide">
    <div class="row between wrapx g20" style="align-items:flex-end; margin-bottom:26px">
      <div>
        <p class="eyebrow">Nổi bật</p>
        <h2 class="h-1" style="margin-top:10px">Bốn không gian mới</h2>
      </div>
      <router-link class="btn btn-secondary" to="/cong-trinh">Xem tất cả công trình</router-link>
    </div>
    <div class="mosaic">
      <SpaceCard v-for="(s, i) in featured" :key="s.id" :space="s"
                 :class="i === 0 ? 'm-wide' : ''"
                 :ratio="i === 0 ? 'l32' : ''" />
    </div>
  </section>

  <!-- Magazine section -->
  <section class="sec sec-line wrap wrap-wide">
    <div class="mag">
      <div class="media p45"><img :src="base + 'img/pic9.jpg'" alt="Không gian nội thất phong cách Indochine" loading="lazy"></div>
      <div>
        <p class="eyebrow">Cách tìm cảm hứng</p>
        <h2 class="h-2" style="margin-top:12px">Một công trình, nhiều không gian, nhiều phong cách</h2>
        <p class="body" style="margin-top:18px">
          Phòng khách của một căn biệt thự có thể mang phong cách Indochine trong khi phòng ngủ lại tối giản.
          Vì vậy mỗi ảnh ở đây được gắn nhãn theo từng không gian, không gộp chung theo dự án.
        </p>
        <p class="body">
          Lọc theo loại phòng, phong cách và tông màu, hoặc mô tả bằng lời điều bạn đang hình dung
          để tìm những không gian gần nhất.
        </p>
        <router-link class="btn btn-secondary" style="margin-top:22px" to="/cong-trinh#phongcach=indochine">
          Xem các không gian Indochine
        </router-link>
      </div>
    </div>
  </section>

  <!-- Hai nhóm -->
  <section class="sec sec-line wrap wrap-wide">
    <p class="eyebrow">Hai nhóm công trình</p>
    <div class="cols t2" style="margin-top:22px">
      <router-link class="pcard" to="/cong-trinh#loai=chung-cu,nha-pho,villa">
        <div class="media l32"><img :src="base + 'img/pic1.jpg'" alt="Không gian nhà ở" loading="lazy"></div>
        <div class="pcard-cap">
          <span class="h-3">Nhà ở</span>
          <span class="small">Chung cư · nhà phố · villa</span>
        </div>
      </router-link>
      <router-link class="pcard" to="/cong-trinh#loai=lounge">
        <div class="media l32"><img :src="base + 'img/pic8.jpg'" alt="Không gian thương mại" loading="lazy"></div>
        <div class="pcard-cap">
          <span class="h-3">Thương mại</span>
          <span class="small">Lounge · F&amp;B · showroom</span>
        </div>
      </router-link>
    </div>
  </section>

  <!-- Lưới đầy đủ -->
  <section v-if="all.length" class="sec sec-line wrap wrap-wide">
    <div class="row between wrapx g20" style="align-items:flex-end; margin-bottom:24px">
      <h2 class="h-2">Tất cả không gian</h2>
      <span class="meta num">{{ all.length }} không gian</span>
    </div>
    <div class="mosaic">
      <SpaceCard v-for="s in all" :key="s.id" :space="s" />
    </div>
    <div style="margin-top:32px">
      <router-link class="btn btn-primary" to="/cong-trinh">Lọc theo nhu cầu của bạn</router-link>
    </div>
  </section>

  <!-- CTA -->
  <section class="sec sec-line wrap wrap-wide">
    <div class="panel" style="display:grid; gap:18px; max-width:66ch">
      <h2 class="h-2">Bạn đang có một không gian cần thiết kế?</h2>
      <p class="body" style="margin:0">
        Hỏi trợ lý ở góc màn hình về phong cách, vật liệu hay các công trình đã làm,
        hoặc để lại thông tin để kiến trúc sư D3 Studio liên hệ với bạn.
      </p>
      <div class="row wrapx g10">
        <router-link class="btn btn-primary" to="/lien-he">Gửi yêu cầu</router-link>
        <router-link class="btn btn-secondary" to="/cong-trinh">Chọn không gian</router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import SpaceCard from '@/components/SpaceCard.vue'
import { usePortfolio } from '@/composables/usePortfolio'

const base = import.meta.env.BASE_URL

const portfolio = usePortfolio()
const all = computed(() => portfolio.spaces)
const featured = computed(() => all.value.slice(-4).reverse()) // the newest
</script>
