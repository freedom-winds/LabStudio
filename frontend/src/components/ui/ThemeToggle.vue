<script setup>
import { computed } from 'vue'
import { Monitor, Moon, Sun } from 'lucide-vue-next'
import { cycleTheme, themeState } from '../../stores/theme'

const icon = computed(() => {
  if (themeState.preference === 'light') return Sun
  if (themeState.preference === 'dark') return Moon
  return Monitor
})

const label = computed(() => {
  if (themeState.preference === 'light') return '浅色模式'
  if (themeState.preference === 'dark') return '暗色模式'
  return `跟随系统：${themeState.resolved === 'dark' ? '暗色' : '浅色'}`
})
</script>

<template>
  <button class="btn ghost theme-toggle" :title="label" :aria-label="label" @click="cycleTheme">
    <component :is="icon" :size="18" :stroke-width="1.75" />
  </button>
</template>
