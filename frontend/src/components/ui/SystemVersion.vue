<script setup>
import versionInfo from '../../version.json'
</script>

<template>
  <footer class="system-version" aria-label="系统版本">
    当前系统版本 v{{ versionInfo.version }}
  </footer>
</template>
