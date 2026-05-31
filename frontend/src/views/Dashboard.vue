<script setup>
import { Bell, CalendarDays, FlaskConical, MessageCircle, Users } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatCard from '../components/ui/StatCard.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { formatDate, humanRole } from '../data/formatters'

const dashboard = ref(null)

onMounted(async () => {
  dashboard.value = await http.get('/api/dashboard')
})
</script>

<template>
  <AppShell>
    <section v-if="dashboard" class="welcome">
      <div class="welcome-user">
        <span class="avatar large">{{ dashboard.user.real_name.slice(0, 1) }}</span>
        <div>
          <h1>{{ dashboard.user.real_name }}，上午好！</h1>
          <div class="badge-row">
            <span class="badge status-pending">{{ humanRole(dashboard.user.account_type) }}</span>
            <span class="badge primary">当前年份 2024年</span>
          </div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 14px">
        <span class="stat-icon"><Bell :size="22" :stroke-width="1.75" /></span>
        <div>
          <strong style="color: var(--text)">你有 {{ dashboard.overview.unread_notifications }} 条未读通知</strong>
          <div style="color: var(--muted); margin-top: 6px">点击查看 latest 通知</div>
        </div>
      </div>
    </section>

    <div v-if="dashboard" class="card-grid" style="margin-top: 24px">
      <StatCard title="我的队伍" :value="dashboard.overview.teams" meta="负责人 2  成员 18" :icon="Users" />
      <StatCard title="我的实验" :value="dashboard.overview.experiments" meta="进行中 12  已完成 12" :icon="FlaskConical" />
      <StatCard title="待处理预约" :value="dashboard.overview.pending_reservations" meta="待审核 5  待确认 2" :icon="CalendarDays" />
      <StatCard title="未读消息" :value="dashboard.overview.unread_messages" meta="@我的 2  系统通知 4" :icon="MessageCircle" />
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
