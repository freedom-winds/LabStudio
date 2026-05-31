<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { FlaskConical } from 'lucide-vue-next'
import { http } from '../api/client'

const router = useRouter()
const password = ref('')
const confirm = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  try {
    await http.post('/api/auth/first-password', { new_password: password.value })
    router.replace('/app')
  } catch (err) {
    error.value = err.message || '修改失败'
  }
}
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="submit">
      <div class="brand">
        <span class="brand-mark"><FlaskConical :size="26" :stroke-width="1.75" /></span>
        <span>首次改密</span>
      </div>
      <div class="form-grid">
        <div class="field">
          <label>新密码</label>
          <input v-model="password" type="password" class="input" />
        </div>
        <div class="field">
          <label>确认密码</label>
          <input v-model="confirm" type="password" class="input" />
        </div>
        <div style="color: var(--muted); line-height: 1.8">
          <div>长度 8 至 16 位。</div>
          <div>至少包含两种字符类型。</div>
          <div>字符类型包括字母、数字、符号。</div>
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <button class="btn primary" type="submit">提交新密码</button>
      </div>
    </form>
  </main>
</template>
