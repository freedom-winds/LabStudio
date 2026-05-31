<script setup>
import { MessageCircle, Plus, Trash2, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { humanRole } from '../data/formatters'

const route = useRoute()
const router = useRouter()
const team = ref(null)
const topics = ref([])
const selectedTopic = ref('')

async function load() {
  team.value = await http.get(`/api/teams/${route.params.id}`)
  topics.value = (await http.get(`/api/topics?year_id=${team.value.year_id}`)).items.filter((topic) => topic.status === 'active')
}

async function addTopic() {
  const ids = new Set(team.value.topics.map((item) => item.id))
  if (selectedTopic.value) ids.add(Number(selectedTopic.value))
  await http.post(`/api/teams/${team.value.id}/topics`, { topic_ids: [...ids] })
  await load()
}

async function removeTopic(topic) {
  const topicIds = team.value.topics.filter((item) => item.id !== topic.id).map((item) => item.id)
  await http.post(`/api/teams/${team.value.id}/topics`, { topic_ids: topicIds })
  await load()
}

async function deleteExperiment(experiment) {
  if (!window.confirm(`确认删除实验「${experiment.name}」？`)) return
  await http.delete(`/api/experiments/${experiment.id}`, { reason: '队伍页删除实验' })
  await load()
}

async function startPrivateChat(user) {
  if (user.id === authState.user?.id) return
  const chat = await http.post('/api/chats', { user_id: user.id })
  router.push(`/app/chats?chat_id=${chat.id}`)
}

onMounted(load)
</script>

<template>
  <AppShell>
    <template v-if="team">
      <section class="card experiment-header">
        <span class="icon-tile"><MessageCircle :size="34" :stroke-width="1.75" /></span>
        <div>
          <div class="badge-row"><StatusBadge :value="team.status" /><span class="badge">所属年份 {{ team.year_id }}</span></div>
          <h1 style="margin: 12px 0; color: var(--text)">{{ team.name }}</h1>
          <div class="meta-row"><span>{{ team.description || '暂无队伍说明' }}</span><span>队伍群聊入口</span></div>
        </div>
        <RouterLink class="btn outline" to="/app/chats">进入群聊</RouterLink>
      </section>

      <section class="card pad" style="margin-bottom: 24px">
        <div class="section-title">
          <div><h3>题目划归</h3><p>从所属年份的题目库中选择，划归后生成队伍实验实例。</p></div>
          <div style="display: flex; gap: 12px">
            <select v-model="selectedTopic" class="select" style="width: 260px">
              <option value="">选择题目</option>
              <option v-for="topic in topics" :key="topic.id" :value="topic.id">{{ topic.title }}</option>
            </select>
            <button class="btn primary" @click="addTopic"><Plus :size="18" />划归题目</button>
          </div>
        </div>
        <div class="badge-row">
          <span v-for="topic in team.topics" :key="topic.id" class="badge primary">
            {{ topic.title }}
            <button class="btn ghost" style="padding: 2px 4px; min-height: auto" title="取消划归" @click="removeTopic(topic)">
              <X :size="14" />
            </button>
          </span>
          <span v-if="!team.topics.length" class="badge">暂无划归题目</span>
        </div>
      </section>

      <section class="card-grid three" style="margin-bottom: 24px">
        <article v-for="experiment in team.experiments" :key="experiment.id" class="card pad">
          <StatusBadge :value="experiment.status" />
          <h3 style="margin-top: 16px">{{ experiment.name }}</h3>
          <p style="color: var(--muted)">最新更新时间 {{ experiment.updated_at }}</p>
          <div style="display: flex; gap: 10px; flex-wrap: wrap">
            <RouterLink class="btn outline" :to="`/app/experiments/${experiment.id}`">进入实验</RouterLink>
            <button class="btn danger" @click="deleteExperiment(experiment)"><Trash2 :size="16" />删除</button>
          </div>
        </article>
      </section>

      <section class="card pad">
        <h3>队伍成员</h3>
        <div class="card-grid three">
          <div v-for="member in team.members" :key="member.id" class="card pad">
            <div style="display: flex; gap: 14px; align-items: center">
              <button
                class="avatar"
                :disabled="member.user.id === authState.user?.id"
                title="发起私聊"
                @click="startPrivateChat(member.user)"
              >
                {{ member.user.real_name.slice(0, 1) }}
              </button>
              <div>
                <strong style="color: var(--text)">{{ member.user.real_name }}</strong>
                <div style="color: var(--muted); font-size: 13px">{{ humanRole(member.role) }}</div>
              </div>
            </div>
            <div class="badge-row" style="margin-top: 14px">
              <span class="badge primary">{{ humanRole(member.role) }}</span>
              <button class="btn ghost" :disabled="member.user.id === authState.user?.id" @click="startPrivateChat(member.user)">
                <MessageCircle :size="16" />私聊
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </AppShell>
</template>
