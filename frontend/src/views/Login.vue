<script setup>
import { FlaskConical, LogIn } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../stores/auth'

const router = useRouter()
const username = ref('00000000')
const password = ref('Admin1234!')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const data = await login(username.value, password.value)
    router.replace(data.requires_password_change ? '/first-password' : '/app')
  } catch (err) {
    error.value = err.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="submit">
      <RouterLink to="/" class="brand">
        <span class="brand-mark"><FlaskConical :size="26" :stroke-width="1.75" /></span>
        <span>Lexy Lab</span>
      </RouterLink>
      <div class="form-grid">
        <div class="field">
          <label>用户名</label>
          <input v-model="username" class="input" maxlength="8" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" class="input" type="password" autocomplete="current-password" />
        </div>
        <p style="margin: 0; color: var(--muted); line-height: 1.7">新账号默认密码等于用户名。首次登录后必须修改密码。</p>
        <div v-if="error" class="error">{{ error }}</div>
        <button class="btn primary" type="submit" :disabled="loading">
          <LogIn :size="18" :stroke-width="1.75" />
          {{ loading ? '登录中' : '登录平台' }}
        </button>
      </div>
    </form>
  </main>
</template>
