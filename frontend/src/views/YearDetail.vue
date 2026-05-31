<script setup>
import { Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'

const route = useRoute()
const year = ref(null)
const topics = ref([])
const teams = ref([])

async function load() {
  year.value = await http.get(`/api/years/${route.params.id}`)
  topics.value = (await http.get(`/api/topics?year_id=${route.params.id}`)).items
  teams.value = (await http.get(`/api/teams?year_id=${route.params.id}`)).items
}

async function deleteTopic(topic) {
  if (!window.confirm(`确认删除题目「${topic.title}」？`)) return
  await http.delete(`/api/topics/${topic.id}`, { reason: '年份详情删除题目' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <template v-if="year">
      <div class="page-title">
        <div>
          <h1>{{ year.name }}</h1>
          <p>年度题目、队伍、公告与群聊入口。</p>
        </div>
        <StatusBadge :value="year.status" />
      </div>
      <div class="card-grid" style="margin-bottom: 24px">
        <article class="card pad"><h3>题目数量</h3><div class="stat-value">{{ year.topics_count }}</div></article>
        <article class="card pad"><h3>队伍数量</h3><div class="stat-value">{{ year.teams_count }}</div></article>
        <article class="card pad"><h3>实验数量</h3><div class="stat-value">{{ year.experiments_count }}</div></article>
        <article class="card pad"><h3>年度管理员</h3><div class="stat-value">{{ year.members.length }}</div></article>
      </div>
      <section class="layout-grid" style="grid-template-columns: 1.2fr 1fr">
        <article class="card pad">
          <h3>年份题目</h3>
          <div class="timeline-list">
            <div v-for="topic in topics" :key="topic.id" class="timeline-item">
              <span class="dot"></span>
              <span><strong style="color: var(--text)">{{ topic.title }}</strong><br />{{ topic.description }}</span>
              <div style="display: flex; gap: 8px; align-items: center">
                <StatusBadge :value="topic.status" />
                <button class="btn danger" @click="deleteTopic(topic)"><Trash2 :size="16" />删除</button>
              </div>
            </div>
          </div>
        </article>
        <article class="card table-card">
          <table class="table">
            <thead><tr><th>队伍</th><th>状态</th><th>入口</th></tr></thead>
            <tbody>
              <tr v-for="team in teams" :key="team.id">
                <td>{{ team.name }}</td>
                <td><StatusBadge :value="team.status" /></td>
                <td><RouterLink class="btn ghost" :to="`/app/teams/${team.id}`">进入</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </article>
      </section>
    </template>
  </AppShell>
</template>
