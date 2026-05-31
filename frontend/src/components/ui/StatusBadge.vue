<script setup>
import { computed } from 'vue'
import { humanStatus } from '../../data/formatters'

const props = defineProps({
  value: { type: String, default: '' },
})

const klass = computed(() => `badge status-${props.value}`)
</script>

<template>
  <span :class="klass">{{ humanStatus(value) }}</span>
</template>
