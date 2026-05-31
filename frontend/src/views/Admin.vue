<script setup>
import { MessageCircle, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { formatDate, humanRole } from '../data/formatters'

const router = useRouter()
const active = ref('users')
const users = ref([])
const logs = ref([])
const form = ref({ username: '20260001', real_name: '新用户', gender: '女', account_type: 'student' })
const error = ref('')

async function load() {
  error.value = ''
  if (active.value === 'users') users.value = (await http.get('/api/users')).items
  if (active.value === 'logs') logs.value = (await http.get('/api/audit-logs')).items
}

async function createUser() {
  try {
    await http.post('/api/users', form.value)
    await load()
  } catch (err) {
    error.value = err.message || '创建用户失败'
  }
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

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>系统管理</h1>
        <p>用户、权限与操作日志管理。点击用户头像可发起私聊。</p>
      </div>
    </div>
    <div class="admin-tabs">
      <button
        v-for="item in [['users','用户管理'],['permissions','权限管理'],['logs','操作日志']]"
        :key="item[0]"
        class="pill-tab"
        :class="{ active: active === item[0] }"
        @click="active = item[0]; load()"
      >
        {{ item[1] }}
      </button>
    </div>
    <section v-if="active === 'users'" class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid" style="grid-template-columns: 140px 160px 120px 160px auto">
        <input v-model="form.username" class="input" maxlength="8" />
        <input v-model="form.real_name" class="input" />
        <select v-model="form.gender" class="select"><option>男</option><option>女</option></select>
        <select v-model="form.account_type" class="select">
          <option value="student">学生</option>
          <option value="teacher">教师</option>
          <option value="admin">系统管理员</option>
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
              <button class="btn ghost" style="gap: 10px" :disabled="user.id === authState.user?.id" @click="startPrivateChat(user)">
                <span class="avatar" style="width: 34px; height: 34px; border-radius: 12px">{{ user.real_name.slice(0, 1) }}</span>
                {{ user.real_name }}
              </button>
            </td>
            <td>{{ user.username }}</td>
            <td>{{ humanRole(user.account_type) }}</td>
            <td>{{ user.gender }}</td>
            <td><StatusBadge :value="user.status" /></td>
            <td style="display: flex; gap: 8px">
              <button class="btn ghost" :disabled="user.id === authState.user?.id" @click="startPrivateChat(user)">
                <MessageCircle :size="16" />私聊
              </button>
              <button class="btn danger" :disabled="user.id === authState.user?.id" @click="deleteUser(user)">
                <Trash2 :size="16" />删除
              </button>
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
            <td>{{ log.actor_id }}</td>
            <td>{{ formatDate(log.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
