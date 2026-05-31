<script setup>
import { EyeOff, Plus, Trash2, Trophy } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { http } from '../api/client'

const honors = ref([])
const form = ref({
  name: '新荣誉成员',
  description: '填写荣誉成就描述。',
  is_visible: true,
  sort_order: 10,
})

async function load() {
  honors.value = (await http.get('/api/honor-members')).items
}

async function create() {
  await http.post('/api/honor-members', form.value)
  await load()
}

async function hide(item) {
  await http.post(`/api/honor-members/${item.id}/hide`)
  await load()
}

async function remove(item) {
  if (!window.confirm(`确认删除荣誉成员「${item.name}」？`)) return
  await http.delete(`/api/honor-members/${item.id}`, { reason: '前端删除' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>荣誉墙管理</h1>
        <p>系统管理员和教师可以维护公开展示的荣誉成员。</p>
      </div>
      <button class="btn primary" @click="create"><Plus :size="18" />添加荣誉成员</button>
    </div>
    <section class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid" style="grid-template-columns: 220px 1fr 120px auto">
        <input v-model="form.name" class="input" />
        <input v-model="form.description" class="input" />
        <input v-model="form.sort_order" class="input" type="number" />
        <button class="btn outline" @click="create">保存</button>
      </div>
    </section>
    <section class="card-grid three">
      <article v-for="member in honors" :key="member.id" class="card pad">
        <span class="stat-icon"><Trophy :size="22" /></span>
        <h3 style="margin-top: 18px">{{ member.name }}</h3>
        <p style="color: var(--muted); line-height: 1.7">{{ member.description }}</p>
        <div class="badge-row">
          <span class="badge primary">排序 {{ member.sort_order }}</span>
          <span class="badge" :class="member.is_visible ? 'status-active' : 'status-ended'">
            {{ member.is_visible ? '展示中' : '已隐藏' }}
          </span>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px">
          <button class="btn outline" @click="hide(member)"><EyeOff :size="16" />隐藏</button>
          <button class="btn danger" @click="remove(member)"><Trash2 :size="16" />删除</button>
        </div>
      </article>
    </section>
  </AppShell>
</template>
