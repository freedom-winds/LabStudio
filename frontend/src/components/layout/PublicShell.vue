<script setup>
import { FlaskConical, LogIn } from 'lucide-vue-next'
import ThemeToggle from '../ui/ThemeToggle.vue'
import SystemVersion from '../ui/SystemVersion.vue'
</script>

<template>
  <div class="public-shell">
    <header class="public-header">
      <RouterLink to="/" class="brand">
        <span class="brand-mark"><FlaskConical :size="26" :stroke-width="1.75" /></span>
        <span>Lexy Lab</span>
      </RouterLink>
      <nav class="public-nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/app/experiments">实验室</RouterLink>
        <RouterLink to="/app/years">研究方向</RouterLink>
        <RouterLink to="/app/teams">成果展示</RouterLink>
        <RouterLink to="/honors">荣誉墙</RouterLink>
        <RouterLink to="/app/toolbox">资源中心</RouterLink>
        <span>关于我们</span>
      </nav>
      <div class="public-actions">
        <ThemeToggle />
        <RouterLink to="/login" class="btn primary">
          <LogIn :size="18" :stroke-width="1.75" />
          登录平台
        </RouterLink>
      </div>
    </header>
    <slot />
    <SystemVersion />
  </div>
</template>
