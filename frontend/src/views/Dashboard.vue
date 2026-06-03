<script setup>
import { Bell, CalendarDays, FlaskConical, MessageCircle, Users } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatCard from '../components/ui/StatCard.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import UserAvatar from '../components/ui/UserAvatar.vue'
import { http } from '../api/client'
import { formatDate, humanRole } from '../data/formatters'

const dashboard = ref(null)
const teamMeta = computed(() => {
  const teams = dashboard.value?.overview_details?.teams || {}
  return `负责人 ${teams.leaders || 0}  成员 ${teams.members || 0}`
})
const experimentMeta = computed(() => {
  const experiments = dashboard.value?.overview_details?.experiments || {}
  return `进行中 ${experiments.working || 0}  已完成 ${experiments.completed || 0}`
})
const reservationMeta = computed(() => {
  const reservations = dashboard.value?.overview_details?.reservations || {}
  return `待审核 ${reservations.pending || 0}  已通过 ${reservations.approved || 0}`
})
const messageMeta = computed(() => {
  const messages = dashboard.value?.overview_details?.messages || {}
  return `未读消息 ${messages.unread_messages || 0}  系统通知 ${messages.unread_notifications || 0}`
})

onMounted(async () => {
  dashboard.value = await http.get('/api/dashboard')
})
</script>

<template>
  <AppShell>
    <section v-if="dashboard" class="welcome">
      <div class="welcome-user">
        <UserAvatar :user="dashboard.user" :size="96" />
        <div>
          <h1>{{ dashboard.user.real_name }}，上午好！</h1>
          <div class="badge-row">
            <span class="badge status-pending">{{ humanRole(dashboard.user.account_type) }}</span>
            <span class="badge primary">当前年份 {{ dashboard.current_year?.name || '未设置' }}</span>
          </div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 14px">
        <span class="stat-icon"><Bell :size="22" :stroke-width="1.75" /></span>
        <div>
          <strong style="color: var(--text)">你有 {{ dashboard.overview.unread_notifications }} 条未读通知</strong>
          <div style="color: var(--muted); margin-top: 6px">点击查看最新通知</div>
        </div>
      </div>
    </section>

    <div v-if="dashboard" class="card-grid" style="margin-top: 24px">
      <StatCard title="我的队伍" :value="dashboard.overview.teams" :meta="teamMeta" :icon="Users" />
      <StatCard title="我的实验" :value="dashboard.overview.experiments" :meta="experimentMeta" :icon="FlaskConical" />
      <StatCard title="待处理预约" :value="dashboard.overview.pending_reservations" :meta="reservationMeta" :icon="CalendarDays" />
      <StatCard title="未读消息" :value="dashboard.overview.unread_messages" :meta="messageMeta" :icon="MessageCircle" />
    </div>

    <section v-if="dashboard" class="layout-grid">
      <article class="card list-card">
        <div class="section-title">
          <h3>近期实验动态</h3>
          <RouterLink class="btn ghost" to="/app/experiments">查看全部</RouterLink>
        </div>
        <div class="timeline-list">
          <div v-for="item in dashboard.recent_activity" :key="item.id" class="timeline-item">
            <span class="dot"></span>
            <span>
              <strong style="color: var(--text)">{{ item.name }}</strong>
              <br />
              队伍实验 · {{ formatDate(item.updated_at) }}
            </span>
            <StatusBadge :value="item.status" />
          </div>
        </div>
      </article>
      <article class="card list-card">
        <div class="section-title">
          <h3>近期公告</h3>
          <RouterLink class="btn ghost" to="/app/announcements">查看全部</RouterLink>
        </div>
        <div class="timeline-list">
          <div v-for="item in dashboard.recent_announcements" :key="item.id" class="timeline-item">
            <span class="dot"></span>
            <span>{{ item.title }}<br /><small>{{ formatDate(item.created_at) }}</small></span>
            <span v-if="item.is_pinned" class="badge status-pending">置顶</span>
          </div>
        </div>
      </article>
      <article class="card list-card">
        <div class="section-title">
          <h3>待处理事项</h3>
          <RouterLink class="btn ghost" to="/app/reservations">查看全部</RouterLink>
        </div>
        <div class="timeline-list">
          <div v-for="item in dashboard.todos" :key="item.id" class="timeline-item">
            <span class="dot" style="background: var(--warning)"></span>
            <span>{{ item.purpose }}<br /><small>{{ formatDate(item.start_time) }}</small></span>
            <StatusBadge :value="item.final_status" />
          </div>
        </div>
      </article>
    </section>
  </AppShell>
</template>
