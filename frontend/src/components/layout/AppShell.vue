<script setup>
import {
  ArrowLeft,
  Bell,
  CalendarDays,
  FlaskConical,
  Home,
  KeyRound,
  LogOut,
  Megaphone,
  MessageCircle,
  Search,
  Settings,
  Trophy,
  Users,
  Wrench,
} from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, loadMe, logout } from '../../stores/auth'
import { humanRole } from '../../data/formatters'
import ThemeToggle from '../ui/ThemeToggle.vue'
import UserAvatar from '../ui/UserAvatar.vue'
import SystemVersion from '../ui/SystemVersion.vue'

const router = useRouter()
const route = useRoute()

const isAdmin = computed(() => authState.user?.account_type === 'admin')
const isTeacher = computed(() => authState.user?.account_type === 'teacher')
const nav = computed(() => [
  { to: '/app', label: '工作台', icon: Home },
  { to: '/app/years', label: '年份', icon: CalendarDays },
  { to: '/app/teams', label: '队伍', icon: Users },
  { to: '/app/experiments', label: '实验', icon: FlaskConical },
  { to: '/app/reservations', label: '预约', icon: CalendarDays },
  { to: '/app/chats', label: '聊天', icon: MessageCircle },
  { to: '/app/announcements', label: '公告', icon: Megaphone },
  { to: '/app/toolbox', label: '工具箱', icon: Wrench },
  { to: isAdmin.value ? '/app/honors' : '/honors', label: isAdmin.value ? '荣誉墙管理' : '荣誉墙', icon: Trophy },
  { to: '/app/admin', label: isAdmin.value ? '系统管理' : isTeacher.value ? '用户管理' : '其他用户', icon: Settings },
])

const mainNavPaths = computed(() => new Set(nav.value.map((item) => item.to)))
const userName = computed(() => authState.user?.real_name || '用户')
const roleName = computed(() => humanRole(authState.user?.account_type))
const showBackButton = computed(() => route.path.startsWith('/app') && !mainNavPaths.value.has(route.path))

onMounted(async () => {
  if (!authState.user) await loadMe().catch(() => router.replace('/login'))
})

async function handleLogout() {
  await logout()
  router.replace('/login')
}

function openChangePassword() {
  router.push('/app/password')
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/app')
}
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <RouterLink to="/app" class="brand">
        <span class="brand-mark"><img src="/nandx.png" alt="" aria-hidden="true" /></span>
        <span>NX Lab</span>
      </RouterLink>
      <nav class="nav-list">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-item">
          <component :is="item.icon" :size="20" :stroke-width="1.75" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="sidebar-note">统一管理年份、队伍、实验、计划、数据与荣誉。</div>
    </aside>
    <section class="main-shell">
      <header class="topbar">
        <div class="topbar-left">
          <button v-if="showBackButton" class="btn ghost back-button" type="button" title="返回上一界面" @click="goBack">
            <ArrowLeft :size="18" :stroke-width="1.75" />
          </button>
          <div class="search">
            <Search :size="18" :stroke-width="1.75" />
            <span>搜索实验、队伍、文档、公告等</span>
          </div>
        </div>
        <div class="top-actions">
          <ThemeToggle />
          <span class="btn ghost"><Bell :size="18" :stroke-width="1.75" /></span>
          <span class="badge primary">{{ roleName }}</span>
          <button class="btn ghost" type="button" @click="openChangePassword">
            <KeyRound :size="18" :stroke-width="1.75" />
            改密
          </button>
          <UserAvatar :user="authState.user" :name="userName" />
          <button class="btn ghost" @click="handleLogout">
            <LogOut :size="18" :stroke-width="1.75" />
            退出
          </button>
        </div>
      </header>
      <main class="content">
        <slot />
      </main>
      <SystemVersion />
    </section>
  </div>
</template>
