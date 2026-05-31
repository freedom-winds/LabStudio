<script setup>
import {
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
import { useRouter } from 'vue-router'
import { authState, loadMe, logout } from '../../stores/auth'
import { humanRole } from '../../data/formatters'
import ThemeToggle from '../ui/ThemeToggle.vue'

const router = useRouter()

const nav = [
  { to: '/app', label: '工作台', icon: Home },
  { to: '/app/years', label: '年份', icon: CalendarDays },
  { to: '/app/teams', label: '队伍', icon: Users },
  { to: '/app/experiments', label: '实验', icon: FlaskConical },
  { to: '/app/reservations', label: '预约', icon: CalendarDays },
  { to: '/app/chats', label: '聊天', icon: MessageCircle },
  { to: '/app/announcements', label: '公告', icon: Megaphone },
  { to: '/app/toolbox', label: '工具箱', icon: Wrench },
  { to: '/app/honors', label: '荣誉墙管理', icon: Trophy },
  { to: '/app/admin', label: '系统管理', icon: Settings },
]

const userName = computed(() => authState.user?.real_name || '用户')
const roleName = computed(() => humanRole(authState.user?.account_type))

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
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <RouterLink to="/app" class="brand">
        <span class="brand-mark"><FlaskConical :size="26" :stroke-width="1.75" /></span>
        <span>Lexy Lab</span>
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
        <div class="search">
          <Search :size="18" :stroke-width="1.75" />
          <span>搜索实验、队伍、文档、公告等</span>
        </div>
        <div class="top-actions">
          <ThemeToggle />
          <span class="btn ghost"><Bell :size="18" :stroke-width="1.75" /></span>
          <span class="badge primary">{{ roleName }}</span>
          <button class="btn ghost" type="button" @click="openChangePassword">
            <KeyRound :size="18" :stroke-width="1.75" />
            改密
          </button>
          <span class="avatar">{{ userName.slice(0, 1) }}</span>
          <button class="btn ghost" @click="handleLogout">
            <LogOut :size="18" :stroke-width="1.75" />
            退出
          </button>
        </div>
      </header>
      <main class="content">
        <slot />
      </main>
    </section>
  </div>
</template>
