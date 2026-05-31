<script setup>
defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  meta: { type: String, default: '' },
  icon: { type: [Object, Function], required: true },
})
</script>

<template>
  <article class="card stat-card">
    <div class="stat-top">
      <span class="stat-icon"><component :is="icon" :size="22" :stroke-width="1.75" /></span>
      <slot name="action" />
    </div>
    <div>
      <div style="color: var(--text); font-weight: 700">{{ title }}</div>
      <div class="stat-value">{{ value }}</div>
      <div style="color: var(--muted); font-size: 13px">{{ meta }}</div>
    </div>
  </article>
</template>
