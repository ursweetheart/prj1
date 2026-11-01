<template>
  <section class="hero hero-show"
           :style="{ '--hero-interval': INTERVAL + 'ms' }"
           role="region" aria-roledescription="carousel" aria-label="Công trình nổi bật"
           @keydown.left.prevent="go(active - 1)"
           @keydown.right.prevent="go(active + 1)">
    <div class="media">
      <img v-for="(s, i) in slides" :key="s.src"
           class="hero-slide" :class="slideClass(i)"
           :src="loaded.has(i) ? s.src : undefined"
           :alt="s.alt" :aria-hidden="i === active ? undefined : 'true'"
           draggable="false"
           :loading="i === 0 ? 'eager' : 'lazy'"
           :fetchpriority="i === 0 ? 'high' : undefined">
    </div>

    <template v-if="many">
      <!-- Hai nửa màn hình: bấm trái về ảnh trước, bấm phải sang ảnh sau -->
      <button type="button" class="hero-side is-prev" aria-label="Ảnh trước" @click="go(active - 1)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>
      </button>
      <button type="button" class="hero-side is-next" aria-label="Ảnh sau" @click="go(active + 1)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>
      </button>

      <div class="hero-dots">
        <button v-for="(s, i) in slides" :key="s.src" type="button"
                class="hero-dot" :class="{ 'is-active': i === active }"
                :aria-label="'Ảnh ' + (i + 1) + ' / ' + slides.length"
                :aria-current="i === active ? 'true' : undefined"
                @click="go(i)">
          <span class="hero-dot-track">
            <span v-if="i === active" :key="cycle" class="hero-dot-fill"></span>
          </span>
        </button>
      </div>
    </template>
  </section>
</template>

<script setup>
/* Màn hình đầu trang chủ: trình chiếu mọi ảnh trong src/assets/hero (theo tên file),
 * mờ dần sang ảnh kế sau 13 giây; bấm nửa trái / phải để lùi / tới;
 * chấm vị trí có thanh tiến trình. */
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

const INTERVAL = 13000   // ms giữa hai lần tự chuyển
const FADE = 1200        // ms, khớp với transition trong app.css

const files = import.meta.glob('../assets/hero/*.{jpg,jpeg,png,webp,avif,JPG,JPEG,PNG,WEBP,AVIF}',
  { eager: true, import: 'default' })

const slides = Object.keys(files)
  .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
  .map(path => ({ src: files[path], alt: altFrom(path) }))

function altFrom(path) {
  const name = path.split('/').pop().replace(/\.[^.]+$/, '').replace(/^\d+[-_ ]*/, '')
  const words = name.split(/[-_ ]+/).filter(Boolean)
    .map(w => w[0].toUpperCase() + w.slice(1)).join(' ')
  return words ? 'D3 Studio - ' + words : 'D3 Studio'
}

const n = slides.length
const many = n > 1
const wrap = i => ((i % n) + n) % n

const active = ref(0)
const under = ref(-1)   // ảnh vừa rời, nằm ngay dưới cho tới khi ảnh mới mờ dần xong
const cycle = ref(0)    // đổi key để chạy lại thanh tiến trình
const loaded = reactive(new Set())

let timer = 0
let underTimer = 0
let reduced = false

function slideClass(i) {
  if (i === active.value) return 'is-active'
  if (i === under.value) return 'is-under'
  return ''
}

function startTimer() {
  clearTimeout(timer)
  cycle.value++
  if (!many || reduced) return
  timer = setTimeout(() => go(active.value + 1), INTERVAL)
}

function go(i) {
  if (!many) return
  const next = wrap(i)
  if (next !== active.value) {
    under.value = active.value
    active.value = next
    clearTimeout(underTimer)
    underTimer = setTimeout(() => { under.value = -1 }, FADE + 100)
  }
  startTimer()
}

// Nạp ảnh hiện tại và hai ảnh kề; ảnh đã nạp thì giữ nguyên
watch(active, i => {
  loaded.add(i)
  if (many) { loaded.add(wrap(i + 1)); loaded.add(wrap(i - 1)) }
}, { immediate: true })

let motionQuery = null
function onMotionChange() {
  reduced = motionQuery.matches
  startTimer()
}

onMounted(() => {
  motionQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)') || null
  reduced = !!motionQuery?.matches
  motionQuery?.addEventListener?.('change', onMotionChange)
  startTimer()
})

onBeforeUnmount(() => {
  clearTimeout(timer)
  clearTimeout(underTimer)
  motionQuery?.removeEventListener?.('change', onMotionChange)
})
</script>
