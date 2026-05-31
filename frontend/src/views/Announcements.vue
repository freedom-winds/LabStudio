<script setup>
import { Megaphone, Plus, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { http } from '../api/client'
import { formatDate } from '../data/formatters'

const announcements = ref([])
const scope = ref('site')
const form = ref({
  scope: 'site',
  title: '实验室安全检查通知',
  content: '请各实验小组完成本周安全检查。',
  is_pinned: false,
})

async function load() {
  announcements.value = (await http.get(`/api/announcements?scope=${scope.value}`)).items
}

async function create() {
  form.value.scope = scope.value
  await http.post('/api/announcements', form.value)
  await load()
}

async function remove(item) {
  if (!window.confirm(`确认删除公告「${item.title}」？`)) return
  await http.delete(`/api/announcements/${item.id}`, { reason: '前端删除' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>公告中心</h1>
        <p>支持全站、年度、队伍与实验范围公告。</p>
      </div>
      <button class="btn primary" @click="create"><Plus :size="18" />发布公告</button>
    </div>
    <div class="admin-tabs">
      <button
        v-for="item in ['site', 'year', 'team', 'experiment']"
        :key="item"
        class="pill-tab"
        :class="{ active: scope === item }"
        @click="scope = item; load()"
      >
        {{ item === 'site' ? '全站' : item === 'year' ? '年度' : item === 'team' ? '队伍' : '实验' }}
      </button>
    </div>
    <section class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid">
        <input v-model="form.title" class="input" />
        <textarea v-model="form.content" class="textarea" />
      </div>
    </section>
    <section class="timeline-list">
      <article
        v-for="item in announcements"
        :key="item.id"
        class="card pad"
        :style="item.is_pinned ? 'background: var(--primary-soft)' : ''"
      >
        <div style="display: flex; gap: 14px; align-items: center">
          <span class="stat-icon"><Megaphone :size="20" /></span>
          <div>
            <h3 style="margin: 0">{{ item.title }}</h3>
            <small style="color: var(--muted)">{{ formatDate(item.created_at) }}</small>
          </div>
          <span v-if="item.is_pinned" class="badge primary" style="margin-left: auto">置顶</span>
          <button class="btn danger" :style="item.is_pinned ? '' : 'margin-left: auto'" @click="remove(item)">
            <Trash2 :size="16" />删除
          </button>
        </div>
        <p style="line-height: 1.8">{{ item.content }}</p>
      </article>
    </section>
  </AppShell>
</template>
