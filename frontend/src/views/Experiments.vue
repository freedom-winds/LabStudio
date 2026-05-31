<script setup>
import { FlaskConical, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { formatDate } from '../data/formatters'

const experiments = ref([])

async function load() {
  experiments.value = (await http.get('/api/experiments')).items
}

async function deleteExperiment(experiment) {
  if (!window.confirm(`确认删除实验「${experiment.name}」？`)) return
  await http.delete(`/api/experiments/${experiment.id}`, { reason: '实验列表删除' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>实验管理</h1>
        <p>按队伍实验实例管理状态、成员、计划、文件、PPT 与公告。</p>
      </div>
    </div>
    <section class="card-grid three">
      <article v-for="experiment in experiments" :key="experiment.id" class="card pad">
        <span class="stat-icon"><FlaskConical :size="22" :stroke-width="1.75" /></span>
        <h3 style="margin-top: 18px">{{ experiment.name }}</h3>
        <div class="badge-row">
          <StatusBadge :value="experiment.status" />
          <span class="badge">队伍 {{ experiment.team_id }}</span>
        </div>
        <p style="color: var(--muted)">更新于 {{ formatDate(experiment.updated_at) }}</p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap">
          <RouterLink class="btn outline" :to="`/app/experiments/${experiment.id}`">进入实验</RouterLink>
          <button class="btn danger" @click="deleteExperiment(experiment)"><Trash2 :size="16" />删除</button>
        </div>
      </article>
    </section>
  </AppShell>
</template>
