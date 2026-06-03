<script setup>
import { MessageCircle, Pencil, Save, Trash2, Upload, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import UserAvatar from '../components/ui/UserAvatar.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { formatDate, humanRole } from '../data/formatters'

const router = useRouter()
const active = ref('users')
const users = ref([])
const logs = ref([])
const userStats = ref(null)
const editingUserId = ref(null)
const editForm = ref({ real_name: '', gender: '女', account_type: 'student', status: 'active' })
const error = ref('')
const isAdmin = computed(() => authState.user?.account_type === 'admin')
const isTeacher = computed(() => authState.user?.account_type === 'teacher')
const canCreateUser = computed(() => isAdmin.value || isTeacher.value)
const canViewUserStats = computed(() => isAdmin.value || isTeacher.value)
const adminTabs = computed(() =>
  isAdmin.value
    ? [['users', '用户管理'], ['permissions', '权限管理'], ['logs', '操作日志']]
    : [['users', isTeacher.value ? '用户管理' : '其他用户']],
)
const currentCohort = new Date().getFullYear() + 2
const defaultUsername = () => `${currentCohort}0101`
const defaultUserForm = () => ({ username: defaultUsername(), real_name: '新用户', gender: '女', account_type: 'student' })
const form = ref(defaultUserForm())

async function load() {
  error.value = ''
  if (!isAdmin.value && active.value !== 'users') active.value = 'users'
  if (active.value === 'users') {
    users.value = (await http.get('/api/users')).items
    userStats.value = canViewUserStats.value ? await http.get('/api/users/stats') : null
  }
  if (active.value === 'logs') logs.value = (await http.get('/api/audit-logs')).items
}

async function createUser() {
  try {
    await http.post('/api/users', form.value)
    form.value = defaultUserForm()
    await load()
  } catch (err) {
    error.value = err.message || '创建用户失败'
  }
}

function canEditUser(user) {
  if (isAdmin.value) return true
  return authState.user?.account_type === 'teacher' && user.account_type === 'student'
}

function startEdit(user) {
  editingUserId.value = user.id
  editForm.value = {
    real_name: user.real_name,
    gender: user.gender,
    account_type: user.account_type,
    status: user.status,
  }
}

async function saveUser(user) {
  const payload = isAdmin.value
    ? { ...editForm.value }
    : { real_name: editForm.value.real_name, gender: editForm.value.gender }
  try {
    await http.patch(`/api/users/${user.id}`, payload)
    editingUserId.value = null
    await load()
  } catch (err) {
    error.value = err.message || '保存用户失败'
  }
}

function cancelEdit() {
  editingUserId.value = null
}

async function deleteUser(user) {
  if (!window.confirm(`确认删除用户「${user.real_name}」？删除后该账号不能登录。`)) return
  await http.delete(`/api/users/${user.id}`, { reason: '管理员删除' })
  await load()
}

async function startPrivateChat(user) {
  if (user.id === authState.user?.id) return
  const chat = await http.post('/api/chats', { user_id: user.id })
  router.push(`/app/chats?chat_id=${chat.id}`)
}

async function uploadAvatar(user, event) {
  const file = event.target.files?.[0]
  if (!file) return
  const body = new FormData()
  body.append('file', file)
  try {
    const updated = await http.post(`/api/users/${user.id}/avatar`, body)
    if (updated.id === authState.user?.id) authState.user = updated
    await load()
  } catch (err) {
    error.value = err.message || '上传头像失败'
  } finally {
    event.target.value = ''
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>{{ isAdmin ? '系统管理' : isTeacher ? '用户管理' : '其他用户' }}</h1>
        <p>{{ isAdmin || isTeacher ? '用户、权限与基础信息管理。点击用户头像可发起私聊。' : '查看平台用户，点击用户头像可发起私聊。' }}</p>
      </div>
    </div>
    <div class="admin-tabs">
      <button
        v-for="item in adminTabs"
        :key="item[0]"
        class="pill-tab"
        :class="{ active: active === item[0] }"
        @click="active = item[0]; load()"
      >
        {{ item[1] }}
      </button>
    </div>
    <section v-if="active === 'users' && canViewUserStats && userStats" class="card pad user-stats-panel">
      <div class="section-title">
        <h3>人员统计</h3>
      </div>
      <div class="user-stats-summary">
        <div class="user-stat-block">
          <span>总人数</span>
          <strong>{{ userStats.total }}</strong>
        </div>
        <div class="user-stat-block">
          <span>学生学号</span>
          <strong>{{ userStats.student_code_total }}</strong>
        </div>
        <div class="user-stat-block">
          <span>教师账号</span>
          <strong>{{ userStats.teacher_account_total }}</strong>
        </div>
        <div class="user-stat-block">
          <span>默认届数</span>
          <strong>{{ currentCohort }}</strong>
        </div>
      </div>
      <div class="user-stats-grid">
        <div>
          <h4>年级人数</h4>
          <div class="stat-table-scroll">
            <table class="table compact">
              <thead><tr><th>年级</th><th>人数</th></tr></thead>
              <tbody>
                <tr v-for="item in userStats.years" :key="item.year">
                  <td>{{ item.year }} 届</td>
                  <td>{{ item.count }}</td>
                </tr>
                <tr v-if="!userStats.years.length"><td colspan="2">暂无数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h4>班级人数</h4>
          <div class="stat-table-scroll">
            <table class="table compact">
              <thead><tr><th>年级</th><th>班级</th><th>人数</th></tr></thead>
              <tbody>
                <tr v-for="item in userStats.classes" :key="`${item.year}-${item.class_no}`">
                  <td>{{ item.year }} 届</td>
                  <td>{{ item.class_no }} 班</td>
                  <td>{{ item.count }}</td>
                </tr>
                <tr v-if="!userStats.classes.length"><td colspan="3">暂无数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
    <section v-if="active === 'users' && canCreateUser" class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid" style="grid-template-columns: 140px 160px 120px 160px auto">
        <input v-model="form.username" class="input" maxlength="8" />
        <input v-model="form.real_name" class="input" />
        <select v-model="form.gender" class="select"><option>男</option><option>女</option></select>
        <select v-model="form.account_type" class="select">
          <option value="student">学生</option>
          <option v-if="isAdmin" value="teacher">教师</option>
          <option v-if="isAdmin" value="admin">系统管理员</option>
        </select>
        <button class="btn primary" @click="createUser">创建用户</button>
      </div>
      <div v-if="error" class="error" style="margin-top: 14px">{{ error }}</div>
    </section>
    <section v-if="active === 'users'" class="card table-card">
      <table class="table">
        <thead><tr><th>用户</th><th>用户名</th><th>身份</th><th>性别</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <input v-if="editingUserId === user.id" v-model="editForm.real_name" class="input" style="width: 140px" />
              <button v-else class="btn ghost" style="gap: 10px" :disabled="user.id === authState.user?.id" @click="startPrivateChat(user)">
                <UserAvatar :user="user" :size="34" />
                {{ user.real_name }}
              </button>
            </td>
            <td>{{ user.username }}</td>
            <td>
              <select v-if="editingUserId === user.id && isAdmin" v-model="editForm.account_type" class="select" style="width: 140px">
                <option value="student">学生</option>
                <option value="teacher">教师</option>
                <option value="admin">系统管理员</option>
              </select>
              <span v-else>{{ humanRole(user.account_type) }}</span>
            </td>
            <td>
              <select v-if="editingUserId === user.id" v-model="editForm.gender" class="select" style="width: 92px">
                <option>男</option>
                <option>女</option>
              </select>
              <span v-else>{{ user.gender }}</span>
            </td>
            <td>
              <select v-if="editingUserId === user.id && isAdmin" v-model="editForm.status" class="select" style="width: 120px">
                <option value="active">启用</option>
                <option value="disabled">禁用</option>
                <option value="deleted">删除</option>
              </select>
              <StatusBadge v-else :value="user.status" />
            </td>
            <td style="display: flex; gap: 8px">
              <template v-if="editingUserId === user.id">
                <button class="btn primary" @click="saveUser(user)"><Save :size="16" />保存</button>
                <button class="btn ghost" @click="cancelEdit"><X :size="16" />取消</button>
              </template>
              <template v-else>
                <button v-if="canEditUser(user)" class="btn outline" @click="startEdit(user)">
                  <Pencil :size="16" />编辑
                </button>
                <button class="btn ghost" :disabled="user.id === authState.user?.id" @click="startPrivateChat(user)">
                  <MessageCircle :size="16" />私聊
                </button>
                <label v-if="canEditUser(user)" class="btn outline">
                  <Upload :size="16" />头像
                  <input hidden type="file" accept="image/png,image/jpeg,image/jpg,image/webp" @change="uploadAvatar(user, $event)" />
                </label>
                <button v-if="isAdmin" class="btn danger" :disabled="user.id === authState.user?.id" @click="deleteUser(user)">
                  <Trash2 :size="16" />删除
                </button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
    <section v-if="active === 'permissions'" class="card pad">
      <h3>权限管理</h3>
      <p style="color: var(--muted); line-height: 1.8">
        平台按系统管理员、教师、年度管理员、队伍领队、队伍成员、实验管理者、实验参与者、实验观察者进行权限并集判断。
      </p>
    </section>
    <section v-if="active === 'logs'" class="card table-card">
      <table class="table">
        <thead><tr><th>操作</th><th>对象</th><th>操作者</th><th>时间</th></tr></thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td>{{ log.action_type }}</td>
            <td>{{ log.object_type }} #{{ log.object_id }}</td>
            <td>{{ log.actor?.real_name || '系统' }}</td>
            <td>{{ formatDate(log.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
