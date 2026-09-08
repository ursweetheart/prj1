<template>
  <div class="palette">
    <div class="sw" v-for="c in palette" :key="c.hex">
      <i :style="{ background: c.hex }" :title="c.hex"></i>
      <span>{{ c.name }}<br><span class="num">{{ c.pct }}%</span></span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  palette: Array
})
</script>
