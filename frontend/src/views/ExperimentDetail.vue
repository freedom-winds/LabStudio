<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, FileText, FlaskConical, Folder, FolderPlus, MessageCircle, Pencil, Plus, Trash2, Upload, UserPlus } from 'lucide-vue-next'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { fileSize, formatDate, humanRole, shortDate } from '../data/formatters'

const route = useRoute()
const router = useRouter()
const active = ref('overview')
const experiment = ref(null)
const phases = ref([])
const selectedPhaseId = ref(null)
const selectedStepId = ref(null)
const stepFiles = ref([])
const workspace = ref({ current_folder: null, breadcrumbs: [], folders: [], files: [] })
const currentWorkspaceFolderId = ref(null)
const presentations = ref([])
const proposals = ref([])
const teamMembers = ref([])
const newPhaseTitle = ref('新阶段')
const newStepTitle = ref('新步骤')
const newFolderName = ref('新文件夹')
const experimentMemberForm = ref({ user_id: '', role: 'participant' })
const draggedPhase = ref(null)
const draggedStep = ref(null)

const tabs = [
  ['overview', '总览'],
  ['plan', '实验计划'],
  ['workspace', '文件存放区'],
  ['files', 'Step 文件'],
  ['ppt', 'PPT 版本'],
  ['proposals', '开题报告'],
  ['members', '成员'],
  ['announcements', '公告'],
  ['chat', '聊天'],
]

const selectedPhase = computed(() => phases.value.find((item) => item.id === selectedPhaseId.value))
const selectedStep = computed(() => selectedPhase.value?.steps?.find((item) => item.id === selectedStepId.value))
const allSteps = computed(() => phases.value.flatMap((p) => p.steps || []))
const completedSteps = computed(() => allSteps.value.filter((s) => s.status === 'done').length)
const totalSteps = computed(() => allSteps.value.length)
const availableExperimentMembers = computed(() => {
  const memberIds = new Set((experiment.value?.members || []).map((member) => member.user_id))
  return teamMembers.value.filter((member) => !memberIds.has(member.user_id))
})
const canManageExperiment = computed(() => ['teacher', 'admin'].includes(authState.user?.account_type))

async function load() {
  experiment.value = await http.get(`/api/experiments/${route.params.id}`)
  const teamDetail = await http.get(`/api/teams/${experiment.value.team_id}`).catch(() => null)
  teamMembers.value = (teamDetail?.members || []).filter(
    (member) => member.user?.account_type === 'student' && member.user?.status === 'active',
  )
  phases.value = await http.get(`/api/experiments/${route.params.id}/phases`)
  presentations.value = await http.get(`/api/experiments/${route.params.id}/presentations`)
  proposals.value = await http.get(`/api/experiments/${route.params.id}/proposals`)
  if (!phases.value.some((phase) => phase.id === selectedPhaseId.value)) {
    selectedPhaseId.value = phases.value[0]?.id || null
  }
  if (!selectedPhase.value?.steps?.some((step) => step.id === selectedStepId.value)) {
    selectedStepId.value = selectedPhase.value?.steps?.[0]?.id || null
  }
  await loadFiles()
  await loadWorkspace()
}

async function loadFiles() {
  if (!selectedStepId.value) {
    stepFiles.value = []
    return
  }
  stepFiles.value = await http.get(`/api/steps/${selectedStepId.value}/files`).catch(() => [])
}

async function loadWorkspace(folderId = currentWorkspaceFolderId.value) {
  const query = folderId ? `?folder_id=${folderId}` : ''
  workspace.value = await http.get(`/api/experiments/${route.params.id}/workspace${query}`)
  currentWorkspaceFolderId.value = workspace.value.current_folder?.id || null
}

async function openWorkspaceFolder(folder) {
  await loadWorkspace(folder?.id || null)
}

async function createWorkspaceFolder() {
  const name = newFolderName.value.trim()
  if (!name) return
  await http.post(`/api/experiments/${route.params.id}/workspace/folders`, {
    name,
    parent_id: currentWorkspaceFolderId.value,
  })
  newFolderName.value = '新文件夹'
  await loadWorkspace()
}

async function renameWorkspaceFolder(folder) {
  const name = window.prompt('修改文件夹名称', folder.name)
  if (!name?.trim()) return
  await http.patch(`/api/experiment-workspace/folders/${folder.id}`, { name: name.trim() })
  await loadWorkspace()
}

async function deleteWorkspaceFolder(folder) {
  if (!window.confirm(`确认删除文件夹「${folder.name}」及其下所有文件？`)) return
  await http.delete(`/api/experiment-workspace/folders/${folder.id}`)
  await loadWorkspace()
}

async function uploadWorkspaceFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  if (currentWorkspaceFolderId.value) form.append('folder_id', currentWorkspaceFolderId.value)
  await http.post(`/api/experiments/${route.params.id}/workspace/files`, form)
  event.target.value = ''
  await loadWorkspace()
}

async function replaceWorkspaceFile(event, fileAsset) {
  const file = event.target.files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  await http.post(`/api/experiment-workspace/files/${fileAsset.id}/replace`, form)
  event.target.value = ''
  await loadWorkspace()
}

async function renameWorkspaceFile(fileAsset) {
  const name = window.prompt('修改文件名称', fileAsset.original_filename)
  if (!name?.trim()) return
  await http.patch(`/api/experiment-workspace/files/${fileAsset.id}`, { name: name.trim() })
  await loadWorkspace()
}

async function deleteWorkspaceFile(fileAsset) {
  if (!window.confirm(`确认删除文件「${fileAsset.original_filename}」？`)) return
  await http.delete(`/api/experiment-workspace/files/${fileAsset.id}`)
  await loadWorkspace()
}

async function addPhase() {
  await http.post(`/api/experiments/${route.params.id}/phases`, { title: newPhaseTitle.value, goal: '补充阶段目标' })
  await load()
}

async function addStep() {
  if (!selectedPhaseId.value) return
  await http.post(`/api/phases/${selectedPhaseId.value}/steps`, { title: newStepTitle.value, content: '补充步骤内容', status: 'todo' })
  await load()
}

async function setExperimentStatus(status) {
  await http.patch(`/api/experiments/${route.params.id}`, { status })
  await load()
}

async function updateStepStatus(step, status) {
  await http.patch(`/api/steps/${step.id}`, { status })
  await load()
}

async function deleteExperiment() {
  if (!window.confirm(`确认删除实验「${experiment.value?.name}」？`)) return
  await http.delete(`/api/experiments/${route.params.id}`, { reason: '前端删除' })
  await router.push('/app/experiments')
}

async function deletePhase(phase) {
  if (!window.confirm(`确认删除 Phase「${phase.title}」？其下 Step 也会被删除。`)) return
  await http.delete(`/api/phases/${phase.id}`, { reason: '前端删除' })
  if (selectedPhaseId.value === phase.id) {
    selectedPhaseId.value = null
    selectedStepId.value = null
  }
  await load()
}

async function deleteStep(step) {
  if (!window.confirm(`确认删除 Step「${step.title}」？`)) return
  await http.delete(`/api/steps/${step.id}`, { reason: '前端删除' })
  if (selectedStepId.value === step.id) selectedStepId.value = null
  await load()
}

async function deleteStepFile(file) {
  if (!window.confirm(`确认删除文件「${file.original_filename}」？`)) return
  await http.delete(`/api/step-files/${file.id}`)
  await loadFiles()
}

async function deletePresentation(version) {
  if (!window.confirm(`确认删除 PPT 版本 v${version.version_no}？`)) return
  await http.delete(`/api/presentations/${version.id}`)
  await load()
}

async function deleteProposal(proposal) {
  if (!window.confirm(`确认删除开题报告「${proposal.title}」？`)) return
  await http.delete(`/api/proposals/${proposal.id}`)
  await load()
}

async function startPrivateChat(user) {
  if (!user?.id) return
  const chat = await http.post('/api/chats', { user_id: user.id })
  await router.push(`/app/chats?chat_id=${chat.id}`)
}

async function upsertExperimentMember(userId = experimentMemberForm.value.user_id, role = experimentMemberForm.value.role) {
  if (!userId) return
  await http.post(`/api/experiments/${route.params.id}/members`, { user_id: Number(userId), role })
  experimentMemberForm.value = { user_id: '', role: 'participant' }
  await load()
}

async function setExperimentMemberRole(member, role) {
  if (member.role === role) return
  await upsertExperimentMember(member.user_id, role)
}

async function removeExperimentMember(member) {
  if (!window.confirm(`确认将「${member.user.real_name}」移出实验？`)) return
  await http.delete(`/api/experiments/${route.params.id}/members/${member.user_id}`)
  await load()
}

async function uploadStepFile(event, category) {
  const file = event.target.files?.[0]
  if (!file || !selectedStepId.value) return
  const form = new FormData()
  form.append('file', file)
  form.append('file_category', category)
  await http.post(`/api/steps/${selectedStepId.value}/files`, form)
  event.target.value = ''
  await loadFiles()
}

async function uploadPpt(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  form.append('change_note', '前端上传的新版本')
  await http.post(`/api/experiments/${route.params.id}/presentations`, form)
  event.target.value = ''
  await load()
}

async function submitProposal(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('title', '我的开题报告')
  form.append('description', '已提交开题报告文件')
  form.append('file', file)
  await http.post(`/api/experiments/${route.params.id}/proposals`, form)
  event.target.value = ''
  await load()
}

async function reorderPhases(targetId) {
  if (!draggedPhase.value || draggedPhase.value === targetId) return
  const list = [...phases.value]
  const from = list.findIndex((item) => item.id === draggedPhase.value)
  const to = list.findIndex((item) => item.id === targetId)
  const [item] = list.splice(from, 1)
  list.splice(to, 0, item)
  await http.post(`/api/experiments/${route.params.id}/phases/reorder`, { ids: list.map((p) => p.id) })
  draggedPhase.value = null
  await load()
}

async function reorderSteps(targetId) {
  if (!draggedStep.value || draggedStep.value === targetId || !selectedPhase.value) return
  const list = [...selectedPhase.value.steps]
  const from = list.findIndex((item) => item.id === draggedStep.value)
  const to = list.findIndex((item) => item.id === targetId)
  const [item] = list.splice(from, 1)
  list.splice(to, 0, item)
  await http.post(`/api/phases/${selectedPhase.value.id}/steps/reorder`, { ids: list.map((s) => s.id) })
  draggedStep.value = null
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <template v-if="experiment">
      <section class="card experiment-header">
        <span class="icon-tile"><FlaskConical :size="36" :stroke-width="1.75" /></span>
        <div>
          <div class="badge-row"><StatusBadge :value="experiment.status" /><span class="badge">2024 年度实验</span></div>
          <h1 style="margin: 12px 0; color: var(--text)">{{ experiment.name }}</h1>
          <div class="meta-row">
            <span>所属队伍：{{ experiment.team?.name || experiment.team_id }}</span>
            <span>实验管理者：{{ experiment.members.find((m) => m.role === 'manager')?.user?.real_name || '-' }}</span>
          </div>
        </div>
        <div style="display: flex; gap: 12px; flex-wrap: wrap">
          <RouterLink to="/app/chats" class="btn outline"><MessageCircle :size="18" />实验群聊</RouterLink>
          <select v-if="canManageExperiment" class="select" style="width: 128px" :value="experiment.status" @change="setExperimentStatus($event.target.value)">
            <option value="working">工作中</option>
            <option value="ramping">磨合中</option>
            <option value="completed">完成</option>
            <option value="abandoned">放弃</option>
          </select>
          <button v-if="canManageExperiment" class="btn danger" @click="deleteExperiment"><Trash2 :size="16" />删除实验</button>
        </div>
      </section>

      <div class="card" style="margin-bottom: 24px">
        <nav class="tabs">
          <button v-for="[key, label] in tabs" :key="key" class="tab" :class="{ active: active === key }" @click="active = key">
            {{ label }}
          </button>
        </nav>
      </div>

      <section v-if="active === 'overview'" class="card-grid" style="margin-bottom: 24px">
        <article class="card pad"><h3>实验状态</h3><StatusBadge :value="experiment.status" /><p>当前阶段：实验实施</p></article>
        <article class="card pad"><h3>阶段进度</h3><div class="stat-value">{{ phases.length }}</div><p>计划阶段</p></article>
        <article class="card pad"><h3>已完成 Step</h3><div class="stat-value">{{ completedSteps }} / {{ totalSteps }}</div></article>
        <article class="card pad"><h3>最新 PPT</h3><p>{{ presentations[0]?.original_filename || '暂无版本' }}</p></article>
      </section>

      <section v-if="active === 'plan'" class="split-plan">
        <article class="card pad">
          <div class="section-title">
            <div><h3>Phase 列表</h3><p>拖拽可调整顺序。</p></div>
          </div>
          <div class="phase-list">
            <div
              v-for="phase in phases"
              :key="phase.id"
              class="phase-card"
              :class="{ active: phase.id === selectedPhaseId }"
              role="button"
              tabindex="0"
              draggable="true"
              @dragstart="draggedPhase = phase.id"
              @dragover.prevent
              @drop="reorderPhases(phase.id)"
              @click="selectedPhaseId = phase.id; selectedStepId = phase.steps?.[0]?.id || null; loadFiles()"
              @keydown.enter="selectedPhaseId = phase.id; selectedStepId = phase.steps?.[0]?.id || null; loadFiles()"
            >
              <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center">
                <strong style="color: var(--text)">{{ phase.title }}</strong>
                <div style="display: flex; gap: 8px; align-items: center">
                  <StatusBadge :value="phase.steps?.some((s) => s.status === 'doing') ? 'doing' : 'todo'" />
                  <button class="btn danger" @click.stop="deletePhase(phase)"><Trash2 :size="16" />删除</button>
                </div>
              </div>
              <span style="text-align: left; color: var(--muted); line-height: 1.6">{{ phase.goal }}</span>
              <small>{{ shortDate(phase.expected_start_date) }} ~ {{ shortDate(phase.expected_end_date) }}</small>
            </div>
            <input v-model="newPhaseTitle" class="input" />
            <button class="btn outline" @click="addPhase"><Plus :size="18" />新建 Phase</button>
          </div>
        </article>
        <article class="card pad">
          <div class="section-title">
            <div><h3>{{ selectedPhase?.title || 'Step 列表' }}</h3><p>{{ selectedPhase?.goal }}</p></div>
            <button class="btn primary" @click="addStep"><Plus :size="18" />新建 Step</button>
          </div>
          <div class="step-list">
            <div
              v-for="(step, index) in selectedPhase?.steps || []"
              :key="step.id"
              class="step-card"
              draggable="true"
              @dragstart="draggedStep = step.id"
              @dragover.prevent
              @drop="reorderSteps(step.id)"
            >
              <span class="number-dot">{{ index + 1 }}</span>
              <div>
                <strong style="color: var(--text)">{{ step.title }}</strong>
                <p style="margin: 6px 0 0; color: var(--muted)">{{ step.content }}</p>
              </div>
              <select class="select" style="width: 120px" :value="step.status" @change="updateStepStatus(step, $event.target.value)">
                <option value="todo">未开始</option>
                <option value="doing">进行中</option>
                <option value="done">已完成</option>
              </select>
              <button class="btn danger" @click="deleteStep(step)"><Trash2 :size="16" />删除</button>
            </div>
          </div>
        </article>
      </section>

      <section v-if="active === 'workspace'" class="card pad">
        <div class="section-title">
          <div>
            <h3>文件存放区</h3>
            <p>实验参与者可创建文件夹、上传文件并替换更新文件。</p>
          </div>
          <label class="btn primary">
            <Upload :size="18" />
            上传文件
            <input hidden type="file" @change="uploadWorkspaceFile" />
          </label>
        </div>
        <div class="badge-row" style="margin-bottom: 18px">
          <button class="btn ghost" @click="openWorkspaceFolder(null)">根目录</button>
          <button
            v-for="folder in workspace.breadcrumbs"
            :key="folder.id"
            class="btn ghost"
            @click="openWorkspaceFolder(folder)"
          >
            {{ folder.name }}
          </button>
        </div>
        <div class="form-grid" style="grid-template-columns: minmax(180px, 1fr) auto; margin-bottom: 18px">
          <input v-model="newFolderName" class="input" placeholder="文件夹名称" />
          <button class="btn outline" @click="createWorkspaceFolder"><FolderPlus :size="18" />创建文件夹</button>
        </div>
        <div class="card-grid three" style="margin-bottom: 24px">
          <article v-for="folder in workspace.folders" :key="folder.id" class="card pad">
            <span class="stat-icon"><Folder :size="22" :stroke-width="1.75" /></span>
            <h3 style="margin-top: 18px">{{ folder.name }}</h3>
            <p style="color: var(--muted)">创建者 {{ folder.creator?.real_name || '-' }}</p>
            <p style="color: var(--muted)">最后编辑 {{ formatDate(folder.updated_at) }}</p>
            <div style="display: flex; gap: 8px; flex-wrap: wrap">
              <button class="btn outline" @click="openWorkspaceFolder(folder)">进入</button>
              <button class="btn ghost" @click="renameWorkspaceFolder(folder)"><Pencil :size="16" />重命名</button>
              <button class="btn danger" @click="deleteWorkspaceFolder(folder)"><Trash2 :size="16" />删除</button>
            </div>
          </article>
        </div>
        <table class="table">
          <thead>
            <tr><th>文件名</th><th>大小</th><th>上传者</th><th>上传时间</th><th>最后编辑</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="file in workspace.files" :key="file.id">
              <td>{{ file.original_filename }}</td>
              <td>{{ fileSize(file.file_size) }}</td>
              <td>{{ file.uploader?.real_name || '-' }}</td>
              <td>{{ formatDate(file.created_at) }}</td>
              <td>{{ formatDate(file.updated_at) }}</td>
              <td style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
                <a class="btn ghost" :href="`/api/experiment-workspace/files/${file.id}/download`"><Download :size="16" />下载</a>
                <label class="btn outline"><Upload :size="16" />替换<input hidden type="file" @change="replaceWorkspaceFile($event, file)" /></label>
                <button class="btn ghost" @click="renameWorkspaceFile(file)"><Pencil :size="16" />重命名</button>
                <button class="btn danger" @click="deleteWorkspaceFile(file)"><Trash2 :size="16" />删除</button>
              </td>
            </tr>
            <tr v-if="!workspace.folders.length && !workspace.files.length">
              <td colspan="6" style="color: var(--muted)">暂无文件。</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="active === 'files'" class="card pad">
        <div class="section-title">
          <div><h3>Step 文件</h3><p>普通实验文件、视频与数据均归属到当前 Step。</p></div>
          <select v-model="selectedStepId" class="select" style="width: 260px" @change="loadFiles">
            <option v-for="step in allSteps" :key="step.id" :value="step.id">{{ step.title }}</option>
          </select>
        </div>
        <div class="layout-grid">
          <article v-for="category in ['document', 'video', 'data']" :key="category" class="card file-section">
            <h3>{{ category === 'document' ? '普通文件' : category === 'video' ? '视频文件' : '数据文件' }}</h3>
            <label class="upload-zone">
              <Upload :size="18" :stroke-width="1.75" />
              点击上传或拖拽文件到此处
              <input hidden type="file" @change="uploadStepFile($event, category)" />
            </label>
            <table class="table">
              <tbody>
                <tr v-for="file in stepFiles.filter((f) => f.file_category === category)" :key="file.id">
                  <td>{{ file.original_filename }}</td>
                  <td>{{ fileSize(file.file_size) }}</td>
                  <td>{{ file.uploader?.real_name || '-' }}</td>
                  <td style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
                    <a class="btn ghost" :href="`/api/step-files/${file.id}/download`"><Download :size="16" />下载</a>
                    <button class="btn danger" @click="deleteStepFile(file)"><Trash2 :size="16" />删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </article>
        </div>
      </section>

      <section v-if="active === 'ppt'" class="card pad">
        <div class="section-title">
          <div><h3>PPT 版本管理</h3><p>每次上传生成新版本，当前版本置顶。</p></div>
          <label class="btn primary"><Upload :size="18" />上传新版本<input hidden type="file" accept=".ppt,.pptx,.pdf" @change="uploadPpt" /></label>
        </div>
        <div class="timeline-list">
          <article v-for="version in presentations" :key="version.id" class="ppt-row" :class="{ current: version.is_current }">
            <strong style="color: var(--primary)">v{{ version.version_no }}</strong>
            <span>{{ version.uploader?.real_name || '-' }}</span>
            <span>{{ formatDate(version.created_at) }}</span>
            <span>{{ version.change_note || '无修改说明' }}</span>
            <a class="btn ghost" :href="`/api/presentations/${version.id}/download`"><Download :size="16" />下载</a>
            <button class="btn danger" @click="deletePresentation(version)"><Trash2 :size="16" />删除</button>
          </article>
        </div>
      </section>

      <section v-if="active === 'proposals'" class="card pad">
        <div class="section-title">
          <div><h3>开题报告</h3><p>参与者只能维护自己的报告，管理者可查看列表。</p></div>
          <label class="btn primary"><FileText :size="18" />提交报告<input hidden type="file" @change="submitProposal" /></label>
        </div>
        <table class="table">
          <thead><tr><th>标题</th><th>提交者</th><th>更新时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="proposal in proposals" :key="proposal.id">
              <td>{{ proposal.title }}</td>
              <td>{{ proposal.submitter?.real_name || '-' }}</td>
              <td>{{ formatDate(proposal.updated_at) }}</td>
              <td style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
                <a v-if="proposal.file_id" class="btn ghost" :href="`/api/proposals/${proposal.id}/download`">下载</a>
                <button class="btn danger" @click="deleteProposal(proposal)"><Trash2 :size="16" />删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="active === 'members'" class="card pad">
        <div class="section-title">
          <div>
            <h3>实验成员</h3>
            <p>从所属队伍学生中选择，设置实验管理员、参与者或观察者。</p>
          </div>
          <div v-if="canManageExperiment" class="form-grid" style="grid-template-columns: minmax(180px, 1fr) 140px auto">
            <select v-model="experimentMemberForm.user_id" class="select">
              <option value="">选择队伍学生</option>
              <option v-for="member in availableExperimentMembers" :key="member.id" :value="member.user_id">
                {{ member.user.real_name }}（{{ humanRole(member.role) }}）
              </option>
            </select>
            <select v-model="experimentMemberForm.role" class="select">
              <option value="manager">实验管理员</option>
              <option value="participant">实验参与者</option>
              <option value="observer">实验观察者</option>
            </select>
            <button class="btn primary" :disabled="!experimentMemberForm.user_id" @click="upsertExperimentMember()">
              <UserPlus :size="18" />加入实验
            </button>
          </div>
        </div>
        <div class="card-grid three">
          <article v-for="member in experiment.members" :key="member.id" class="card pad">
            <div style="display: flex; gap: 14px; align-items: center">
              <button class="avatar" :title="`私聊 ${member.user.real_name}`" @click="startPrivateChat(member.user)">
                {{ member.user.real_name.slice(0, 1) }}
              </button>
              <div>
                <strong style="color: var(--text)">{{ member.user.real_name }}</strong>
                <div style="color: var(--muted)">{{ humanRole(member.role) }}</div>
              </div>
            </div>
            <div class="badge-row" style="margin-top: 14px">
              <select v-if="canManageExperiment" class="select" style="width: 148px" :value="member.role" @change="setExperimentMemberRole(member, $event.target.value)">
                <option value="manager">实验管理员</option>
                <option value="participant">实验参与者</option>
                <option value="observer">实验观察者</option>
              </select>
              <span v-else class="badge primary">{{ humanRole(member.role) }}</span>
              <button v-if="canManageExperiment" class="btn danger" @click="removeExperimentMember(member)">
                <Trash2 :size="16" />移出
              </button>
            </div>
          </article>
        </div>
      </section>

      <section v-if="active === 'announcements'" class="card pad">
        <h3>实验公告</h3>
        <div class="timeline-list">
          <div v-for="item in experiment.announcements" :key="item.id" class="timeline-item">
            <span class="dot"></span>
            <span><strong style="color: var(--text)">{{ item.title }}</strong><br />{{ item.content }}</span>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </section>

      <section v-if="active === 'chat'" class="card pad">
        <h3>实验群聊</h3>
        <p style="color: var(--muted)">聊天模块在消息中心展示，会话列表与消息流分屏显示。</p>
        <RouterLink class="btn primary" to="/app/chats"><MessageCircle :size="18" />进入消息中心</RouterLink>
      </section>
    </template>
  </AppShell>
</template>
