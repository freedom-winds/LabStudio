<script setup>
import { Plus, Trash2, Users } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'

const teams = ref([])
const years = ref([])
const form = ref({ name: '先进材料科研组', year_id: '', description: '材料制备与性能表征方向。' })

async function load() {
  teams.value = (await http.get('/api/teams')).items
  years.value = (await http.get('/api/years')).items
  if (!form.value.year_id && years.value[0]) form.value.year_id = years.value[0].id
}

async function createTeam() {
  await http.post('/api/teams', form.value)
  await load()
}

async function deleteTeam(team) {
  if (!window.confirm(`确认删除队伍「${team.name}」？`)) return
  await http.delete(`/api/teams/${team.id}`, { reason: '队伍列表删除' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>队伍管理</h1>
        <p>创建队伍、维护成员与关联实验题目。</p>
      </div>
      <button class="btn primary" @click="createTeam">
        <Plus :size="18" :stroke-width="1.75" />
        新建队伍
      </button>
    </div>
    <section class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid" style="grid-template-columns: 1fr 180px 1.4fr auto">
        <input v-model="form.name" class="input" />
        <select v-model="form.year_id" class="select">
          <option value="">选择年份</option>
          <option v-for="year in years" :key="year.id" :value="year.id">{{ year.name }}</option>
        </select>
        <input v-model="form.description" class="input" />
        <button class="btn outline" @click="createTeam">保存</button>
      </div>
    </section>
    <section class="card-grid three">
      <article v-for="team in teams" :key="team.id" class="card pad">
        <span class="stat-icon"><Users :size="22" :stroke-width="1.75" /></span>
        <h3 style="margin-top: 18px">{{ team.name }}</h3>
        <p style="color: var(--muted); line-height: 1.7">{{ team.description || '暂无描述' }}</p>
        <div class="badge-row">
          <StatusBadge :value="team.status" />
          <span class="badge">年度 ID {{ team.year_id }}</span>
        </div>
        <div style="display: flex; gap: 10px; margin-top: 18px; flex-wrap: wrap">
          <RouterLink class="btn outline" :to="`/app/teams/${team.id}`">进入队伍</RouterLink>
          <button class="btn danger" @click="deleteTeam(team)"><Trash2 :size="16" />删除</button>
        </div>
      </article>
    </section>
  </AppShell>
</template>
