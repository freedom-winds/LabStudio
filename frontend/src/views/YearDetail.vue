<script setup>
import { Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'

const route = useRoute()
const year = ref(null)
const canManageYear = computed(() => ['teacher', 'admin'].includes(authState.user?.account_type))
const topics = ref([])
const teams = ref([])
const editingTopicId = ref(null)
const topicForm = ref({
  title: '',
  description: '',
  status: 'active',
})

async function load() {
  year.value = await http.get(`/api/years/${route.params.id}`)
  topics.value = (await http.get(`/api/topics?year_id=${route.params.id}`)).items
  teams.value = (await http.get(`/api/teams?year_id=${route.params.id}`)).items
}

function resetTopicForm() {
  editingTopicId.value = null
  topicForm.value = {
    title: '',
    description: '',
    status: 'active',
  }
}

function editTopic(topic) {
  editingTopicId.value = topic.id
  topicForm.value = {
    title: topic.title,
    description: topic.description || '',
    status: topic.status || 'active',
  }
}

async function saveTopic() {
  const payload = {
    year_id: Number(route.params.id),
    title: topicForm.value.title.trim(),
    description: topicForm.value.description.trim(),
    status: topicForm.value.status,
  }
  if (!payload.title) return
  if (editingTopicId.value) {
    await http.patch(`/api/topics/${editingTopicId.value}`, payload)
  } else {
    await http.post('/api/topics', payload)
  }
  resetTopicForm()
  await load()
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
      <section v-if="canManageYear" class="card form-card" style="margin-bottom: 24px">
        <div class="section-title">
          <div>
            <h3>{{ editingTopicId ? '修改年份题目' : '添加年份题目' }}</h3>
            <p>题目归属于年份，队伍只从年份题目库中选择划归。</p>
          </div>
          <button v-if="editingTopicId" class="btn ghost" @click="resetTopicForm">
            <X :size="16" />取消修改
          </button>
        </div>
        <div class="form-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr))">
          <input v-model="topicForm.title" class="input" placeholder="题目名称" />
          <input v-model="topicForm.description" class="input" placeholder="题目说明" />
          <select v-model="topicForm.status" class="select">
            <option value="active">启用</option>
            <option value="disabled">停用</option>
          </select>
          <button class="btn primary" @click="saveTopic">
            <Plus v-if="!editingTopicId" :size="18" />
            <Pencil v-else :size="18" />
            {{ editingTopicId ? '保存修改' : '添加题目' }}
          </button>
        </div>
      </section>
      <section class="layout-grid" style="grid-template-columns: 1.2fr 1fr">
        <article class="card pad">
          <h3>年份题目</h3>
          <div class="timeline-list">
            <div v-for="topic in topics" :key="topic.id" class="timeline-item">
              <span class="dot"></span>
              <span><strong style="color: var(--text)">{{ topic.title }}</strong><br />{{ topic.description }}</span>
              <div style="display: flex; gap: 8px; align-items: center">
                <StatusBadge :value="topic.status" />
                <button v-if="canManageYear" class="btn outline" @click="editTopic(topic)"><Pencil :size="16" />修改</button>
                <button v-if="canManageYear" class="btn danger" @click="deleteTopic(topic)"><Trash2 :size="16" />删除</button>
              </div>
            </div>
            <div v-if="!topics.length" class="timeline-item">
              <span class="dot"></span>
              <span>暂无题目，先在上方添加年份题目。</span>
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
