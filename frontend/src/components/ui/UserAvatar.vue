<script setup>
import { computed } from 'vue'

const props = defineProps({
  user: { type: Object, default: null },
  name: { type: String, default: '' },
  size: { type: Number, default: 52 },
})

const displayName = computed(() => props.name || props.user?.real_name || props.user?.name || '用户')
const avatarUrl = computed(() => props.user?.avatar_url || '')
const initial = computed(() => displayName.value.slice(0, 1) || '?')
const avatarStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  borderRadius: props.size >= 72 ? '18px' : '12px',
  fontSize: props.size >= 72 ? '30px' : '14px',
}))
</script>

<template>
  <span class="avatar user-avatar" :style="avatarStyle">
    <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" loading="lazy" />
    <span v-else>{{ initial }}</span>
  </span>
</template>
