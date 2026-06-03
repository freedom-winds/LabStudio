<script setup>
import { MessageCircle, Plus, Trash2, UserPlus, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import UserAvatar from '../components/ui/UserAvatar.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { humanRole } from '../data/formatters'

const route = useRoute()
const router = useRouter()
const team = ref(null)
const topics = ref([])
const students = ref([])
const selectedTopic = ref('')
const memberForm = ref({ user_id: '', role: 'member' })
const canManageTeam = computed(() => ['teacher', 'admin'].includes(authState.user?.account_type))
const sortedExperiments = computed(() =>
  [...(team.value?.experiments || [])].sort((a, b) => {
    if (a.is_my_experiment !== b.is_my_experiment) return a.is_my_experiment ? -1 : 1
    return String(b.updated_at || '').localeCompare(String(a.updated_at || ''))
  }),
)

const availableStudents = computed(() => {
  const memberIds = new Set((team.value?.members || []).map((member) => member.user_id))
  return students.value.filter((student) => !memberIds.has(student.id))
})

async function load() {
  team.value = await http.get(`/api/teams/${route.params.id}`)
  topics.value = (await http.get(`/api/topics?year_id=${team.value.year_id}`)).items.filter((topic) => topic.status === 'active')
  students.value = (await http.get('/api/users')).items.filter((user) => user.account_type === 'student' && user.status === 'active')
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

async function upsertTeamMember(userId = memberForm.value.user_id, role = memberForm.value.role) {
  if (!userId) return
  await http.post(`/api/teams/${team.value.id}/members`, { user_id: Number(userId), role })
  memberForm.value = { user_id: '', role: 'member' }
  await load()
}

async function setTeamMemberRole(member, role) {
  if (member.role === role) return
  await upsertTeamMember(member.user_id, role)
}

async function removeTeamMember(member) {
  if (!window.confirm(`确认将「${member.user.real_name}」移出队伍？`)) return
  await http.delete(`/api/teams/${team.value.id}/members/${member.user_id}`)
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

      <section v-if="canManageTeam" class="card pad" style="margin-bottom: 24px">
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
        <article v-for="experiment in sortedExperiments" :key="experiment.id" class="card pad">
          <StatusBadge :value="experiment.status" />
          <h3 style="margin-top: 16px">{{ experiment.name }}</h3>
          <div v-if="experiment.is_my_experiment || !canManageTeam" class="badge-row" style="margin-bottom: 12px">
            <span v-if="experiment.is_my_experiment" class="badge primary">
              我参与 · {{ humanRole(experiment.my_role) }}
            </span>
            <span v-else-if="!canManageTeam" class="badge">未加入该实验</span>
          </div>
          <p style="color: var(--muted)">最新更新时间 {{ experiment.updated_at }}</p>
          <div style="display: flex; gap: 10px; flex-wrap: wrap">
            <RouterLink class="btn outline" :to="`/app/experiments/${experiment.id}?team_id=${team.id}`">进入实验</RouterLink>
            <button v-if="canManageTeam" class="btn danger" @click="deleteExperiment(experiment)"><Trash2 :size="16" />删除</button>
          </div>
        </article>
      </section>

      <section class="card pad">
        <div class="section-title">
          <div>
            <h3>队伍成员</h3>
            <p>将学生加入队伍，并设置队伍成员或领队身份。</p>
          </div>
          <div v-if="canManageTeam" class="form-grid" style="grid-template-columns: minmax(180px, 1fr) 130px auto">
            <select v-model="memberForm.user_id" class="select">
              <option value="">选择学生</option>
              <option v-for="student in availableStudents" :key="student.id" :value="student.id">
                {{ student.real_name }}
              </option>
            </select>
            <select v-model="memberForm.role" class="select">
              <option value="member">队伍成员</option>
              <option value="leader">队伍领队</option>
            </select>
            <button class="btn primary" :disabled="!memberForm.user_id" @click="upsertTeamMember()">
              <UserPlus :size="18" />加入队伍
            </button>
          </div>
        </div>
        <div class="card-grid three">
          <div v-for="member in team.members" :key="member.id" class="card pad">
            <div style="display: flex; gap: 14px; align-items: center">
              <button
                class="avatar-button"
                :disabled="member.user.id === authState.user?.id"
                title="发起私聊"
                @click="startPrivateChat(member.user)"
              >
                <UserAvatar :user="member.user" />
              </button>
              <div>
                <strong style="color: var(--text)">{{ member.user.real_name }}</strong>
                <div style="color: var(--muted); font-size: 13px">{{ humanRole(member.role) }}</div>
              </div>
            </div>
            <div class="badge-row" style="margin-top: 14px">
              <select v-if="canManageTeam" class="select" style="width: 132px" :value="member.role" @change="setTeamMemberRole(member, $event.target.value)">
                <option value="member">队伍成员</option>
                <option value="leader">队伍领队</option>
              </select>
              <span v-else class="badge primary">{{ humanRole(member.role) }}</span>
              <button class="btn ghost" :disabled="member.user.id === authState.user?.id" @click="startPrivateChat(member.user)">
                <MessageCircle :size="16" />私聊
              </button>
              <button v-if="canManageTeam" class="btn danger" :disabled="member.user_id === team.creator_id" @click="removeTeamMember(member)">
                <Trash2 :size="16" />移出
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </AppShell>
</template>
