<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import { http } from '../api/client'

const router = useRouter()
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref('')

async function submit() {
  error.value = ''
  success.value = ''
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的新密码不一致'
    return
  }
  try {
    await http.post('/api/auth/password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    success.value = '密码已修改'
  } catch (err) {
    error.value = err.message || '修改失败'
  }
}
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>修改密码</h1>
        <p>登录用户可在这里修改自己的密码。</p>
      </div>
      <RouterLink class="btn ghost" to="/app">返回工作台</RouterLink>
    </div>
    <form class="card form-card" style="max-width: 520px" @submit.prevent="submit">
      <div class="form-grid">
        <div class="field">
          <label>当前密码</label>
          <input v-model="oldPassword" class="input" type="password" autocomplete="current-password" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="newPassword" class="input" type="password" autocomplete="new-password" />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input v-model="confirmPassword" class="input" type="password" autocomplete="new-password" />
        </div>
        <div style="color: var(--muted); line-height: 1.8">
          <div>长度 8 至 16 位。</div>
          <div>至少包含字母、数字、符号中的两类。</div>
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <div v-if="success" class="badge status-active" style="justify-self: start">{{ success }}</div>
        <button class="btn primary" type="submit">保存新密码</button>
      </div>
    </form>
  </AppShell>
</template>
