<script setup>
import { FlaskConical, Plus, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { formatDate } from '../data/formatters'

const experiments = ref([])
const teams = ref([])
const topics = ref([])
const creating = ref(false)
const error = ref('')
const form = ref({
  team_id: '',
  topic_id: '',
  name: '',
  status: 'working',
})

async function load() {
  const [experimentData, teamData] = await Promise.all([http.get('/api/experiments'), http.get('/api/teams')])
  experiments.value = experimentData.items
  teams.value = teamData.items
  if (!form.value.team_id && teams.value[0]) {
    form.value.team_id = teams.value[0].id
    await loadTopics()
  }
}

async function loadTopics() {
  const team = teams.value.find((item) => item.id === Number(form.value.team_id))
  form.value.topic_id = ''
  topics.value = []
  if (!team) return
  topics.value = (await http.get(`/api/topics?year_id=${team.year_id}`)).items.filter((topic) => topic.status === 'active')
  if (topics.value[0]) form.value.topic_id = topics.value[0].id
}

async function createExperiment() {
  error.value = ''
  if (!form.value.team_id || !form.value.topic_id) {
    error.value = '请选择队伍和题目后再创建实验。'
    return
  }
  creating.value = true
  try {
    await http.post('/api/experiments', {
      team_id: Number(form.value.team_id),
      topic_id: Number(form.value.topic_id),
      name: form.value.name.trim(),
      status: form.value.status,
    })
    form.value.name = ''
    await load()
  } catch (err) {
    error.value = err.message || '创建实验失败'
  } finally {
    creating.value = false
  }
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
      <button class="btn primary" :disabled="creating" @click="createExperiment">
        <Plus :size="18" :stroke-width="1.75" />
        新建实验
      </button>
    </div>
    <section class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr))">
        <select v-model="form.team_id" class="select" @change="loadTopics">
          <option value="">选择队伍</option>
          <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
        </select>
        <select v-model="form.topic_id" class="select">
          <option value="">选择题目</option>
          <option v-for="topic in topics" :key="topic.id" :value="topic.id">{{ topic.title }}</option>
        </select>
        <input v-model="form.name" class="input" placeholder="实验名称，留空使用题目名称" />
        <select v-model="form.status" class="select">
          <option value="working">工作中</option>
          <option value="ramping">磨合中</option>
          <option value="completed">完成</option>
          <option value="abandoned">放弃</option>
        </select>
        <button class="btn outline" :disabled="creating" @click="createExperiment">保存</button>
      </div>
      <p v-if="error" class="error" style="margin-bottom: 0">{{ error }}</p>
    </section>
    <section class="card-grid three">
      <article v-for="experiment in experiments" :key="experiment.id" class="card pad">
        <span class="stat-icon"><FlaskConical :size="22" :stroke-width="1.75" /></span>
        <h3 style="margin-top: 18px">{{ experiment.name }}</h3>
        <div class="badge-row">
          <StatusBadge :value="experiment.status" />
          <span class="badge">队伍 {{ experiment.team?.name || experiment.team_id }}</span>
          <span class="badge">题目 {{ experiment.topic?.title || experiment.topic_id }}</span>
        </div>
        <p style="color: var(--muted)">更新于 {{ formatDate(experiment.updated_at) }}</p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap">
          <RouterLink class="btn outline" :to="`/app/experiments/${experiment.id}`">进入实验</RouterLink>
          <button class="btn danger" @click="deleteExperiment(experiment)"><Trash2 :size="16" />删除</button>
        </div>
      </article>
      <article v-if="!experiments.length" class="card pad">
        <span class="stat-icon"><FlaskConical :size="22" :stroke-width="1.75" /></span>
        <h3 style="margin-top: 18px">暂无实验</h3>
        <p style="color: var(--muted)">选择队伍和题目后即可创建第一个实验。</p>
      </article>
    </section>
  </AppShell>
</template>
