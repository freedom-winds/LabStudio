<script setup>
import { CalendarDays, Database, FlaskConical, FolderOpen, LogIn, Trophy } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import PublicShell from '../components/layout/PublicShell.vue'
import { http } from '../api/client'

const honors = ref([])

onMounted(async () => {
  honors.value = await http.get('/api/public/honor-members').catch(() => [])
})
</script>

<template>
  <PublicShell>
    <section class="container hero">
      <div>
        <div class="hero-label">
          <FlaskConical :size="18" :stroke-width="1.75" />
          面向实验室的全流程数字化管理
        </div>
        <h1>实验室垂直管理平台</h1>
        <p>统一管理年份、队伍、实验、计划、数据、预约与荣誉，助力实验室高效协同与持续创新。</p>
        <div class="hero-actions">
          <RouterLink to="/login" class="btn primary">
            <LogIn :size="20" :stroke-width="1.75" />
            登录平台
          </RouterLink>
          <RouterLink to="/honors" class="btn outline">
            <Trophy :size="20" :stroke-width="1.75" />
            荣誉墙
          </RouterLink>
        </div>
      </div>
      <div class="lab-visual" aria-hidden="true">
        <div class="floating-panel folder-panel"><FolderOpen :size="38" :stroke-width="1.75" /></div>
        <div class="floating-panel calendar-panel">
          <strong style="color: var(--text)">实验室日程</strong>
          <div style="margin-top: 12px; color: var(--muted); line-height: 1.8">预约记录<br />实时同步</div>
        </div>
        <div class="mock-window">
          <h3 style="margin: 0; color: var(--text)">欢迎回来，NX Lab</h3>
          <p style="margin: 8px 0 0; color: var(--muted)">探索实验室的最新动态</p>
          <div class="mock-grid">
            <div class="mock-card"><FlaskConical color="#2563eb" /><strong>实时</strong><span>实验项目</span></div>
            <div class="mock-card"><CalendarDays color="#0f766e" /><strong>同步</strong><span>实验计划</span></div>
            <div class="mock-card"><Database color="#2563eb" /><strong>归档</strong><span>数据集</span></div>
            <div class="mock-card"><CalendarDays color="#d97706" /><strong>实时</strong><span>预约</span></div>
          </div>
          <div class="card-grid three" style="grid-template-columns: 1fr 1fr; margin-top: 22px">
            <div class="card pad">
              <h3>近期实验计划</h3>
              <div class="timeline-list">
                <div class="timeline-item"><span class="dot"></span><span>高性能有机材料电化学性能研究</span><span class="badge primary">进行中</span></div>
                <div class="timeline-item"><span class="dot" style="background: var(--warning)"></span><span>数据分析与建模</span><span class="badge status-pending">待开始</span></div>
              </div>
            </div>
            <div class="card pad">
              <h3>快捷入口</h3>
              <div class="badge-row">
                <span class="badge primary">实验管理</span>
                <span class="badge">数据管理</span>
                <span class="badge">设备预约</span>
                <span class="badge">文件资源</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="container honor-section">
      <div class="section-title">
        <div>
          <h2>荣誉墙</h2>
          <p>致敬卓越，见证实验室的荣誉与成就。</p>
        </div>
        <RouterLink to="/honors" class="btn outline">查看全部荣誉</RouterLink>
      </div>
      <div class="card-grid">
        <article v-for="member in honors.slice(0, 4)" :key="member.id" class="card honor-card">
          <span class="avatar large">{{ member.name.slice(0, 1) }}</span>
          <div>
            <h3 style="margin: 0 0 8px; color: var(--text)">{{ member.name }}</h3>
            <span class="badge status-pending">实验室荣誉成员</span>
            <p style="color: var(--muted); line-height: 1.7">{{ member.description }}</p>
          </div>
        </article>
      </div>
    </section>
  </PublicShell>
</template>
