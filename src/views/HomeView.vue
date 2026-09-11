<template>
  <!-- Hero -->
  <section class="hero">
    <div class="media"><img :src="base + 'img/indochine-apartment-hero.jpg'" alt="D3 Studio - Indochine Apartment"></div>
  </section>

  <!-- Nổi bật -->
  <section class="sec wrap wrap-wide">
    <div class="row between wrapx g20" style="align-items:flex-end; margin-bottom:26px">
      <div>
        <p class="eyebrow">Praeclara</p>
        <h2 class="h-1" style="margin-top:10px">Quattuor spatia recentia</h2>
      </div>
      <router-link class="btn btn-secondary" to="/cong-trinh">Omnia opera</router-link>
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
      <div class="media p45"><img :src="base + 'img/pic9.jpg'" alt="Lorem ipsum dolor sit amet" loading="lazy"></div>
      <div>
        <p class="eyebrow">Quomodo facimus</p>
        <h2 class="h-2" style="margin-top:12px">Unum opus saepe multos modos habet</h2>
        <p class="body" style="margin-top:18px">
          Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed ut perspiciatis
          unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
          totam rem aperiam, eaque ipsa quae ab illo inventore veritatis.
        </p>
        <p class="body">
          Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit,
          sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.
          Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet.
        </p>
        <router-link class="btn btn-secondary" style="margin-top:22px" to="/cong-trinh#phongcach=indochine">
          Lorem ipsum spatia
        </router-link>
      </div>
    </div>
  </section>

  <!-- Hai nhóm -->
  <section class="sec sec-line wrap wrap-wide">
    <p class="eyebrow">Duo genera operum</p>
    <div class="cols t2" style="margin-top:22px">
      <router-link class="pcard" to="/cong-trinh#loai=chung-cu,nha-pho,villa">
        <div class="media l32"><img :src="base + 'img/pic1.jpg'" alt="Lorem ipsum" loading="lazy"></div>
        <div class="pcard-cap">
          <span class="h-3">Nhà ở</span>
          <span class="small">Chung cư · nhà phố · villa</span>
        </div>
      </router-link>
      <router-link class="pcard" to="/cong-trinh#loai=lounge">
        <div class="media l32"><img :src="base + 'img/pic8.jpg'" alt="Lorem ipsum" loading="lazy"></div>
        <div class="pcard-cap">
          <span class="h-3">Thương mại</span>
          <span class="small">Lounge · F&amp;B · showroom</span>
        </div>
      </router-link>
    </div>
  </section>

  <!-- Lưới đầy đủ -->
  <section class="sec sec-line wrap wrap-wide">
    <div class="row between wrapx g20" style="align-items:flex-end; margin-bottom:24px">
      <h2 class="h-2">Omnia spatia</h2>
      <span class="meta num">{{ all.length }} không gian</span>
    </div>
    <div class="mosaic">
      <SpaceCard v-for="s in all" :key="s.id" :space="s" />
    </div>
    <div style="margin-top:32px">
      <router-link class="btn btn-primary" to="/cong-trinh">Lorem ipsum, dolor sit, amet consectetur</router-link>
    </div>
  </section>

  <!-- CTA -->
  <section class="sec sec-line wrap wrap-wide">
    <div class="panel" style="display:grid; gap:18px; max-width:66ch">
      <h2 class="h-2">Habetisne locum quem facere vultis?</h2>
      <p class="body" style="margin:0">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
        quis nostrud exercitation ullamco laboris.
      </p>
      <div class="row wrapx g10">
        <router-link class="btn btn-primary" to="/lien-he">Mittere petitionem</router-link>
        <router-link class="btn btn-secondary" to="/cong-trinh">Eligere spatia</router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import { SPACES } from '@/data'
import SpaceCard from '@/components/SpaceCard.vue'

const base = import.meta.env.BASE_URL
const featured = [SPACES[3], SPACES[0], SPACES[2], SPACES[4]].filter(Boolean)
const all = SPACES
</script>
