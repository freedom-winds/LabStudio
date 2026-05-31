<script setup>
import { CalendarPlus, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { formatDate } from '../data/formatters'

const years = ref([])
const name = ref('2026 年度实验')
const yearNumber = ref(2026)

async function load() {
  const data = await http.get('/api/years')
  years.value = data.items
}

async function createYear() {
  await http.post('/api/years', { name: name.value, year_number: Number(yearNumber.value) })
  await load()
}

async function deleteYear(year) {
  if (!window.confirm(`确认删除年份「${year.name}」？`)) return
  await http.delete(`/api/years/${year.id}`, { reason: '年份列表删除' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>年份管理</h1>
        <p>按年度组织题目、队伍、实验实例、公告与成员身份。</p>
      </div>
      <button class="btn primary" @click="createYear">
        <CalendarPlus :size="18" :stroke-width="1.75" />
        新建年份
      </button>
    </div>
    <section class="card form-card" style="margin-bottom: 24px">
      <div class="form-grid" style="grid-template-columns: 1fr 180px auto">
        <input v-model="name" class="input" />
        <input v-model="yearNumber" class="input" type="number" />
        <button class="btn outline" @click="createYear">保存</button>
      </div>
    </section>
    <section class="card table-card">
      <table class="table">
        <thead>
          <tr><th>年份名称</th><th>年份数值</th><th>状态</th><th>创建时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="year in years" :key="year.id">
            <td>{{ year.name }}</td>
            <td>{{ year.year_number }}</td>
            <td><StatusBadge :value="year.status" /></td>
            <td>{{ formatDate(year.created_at) }}</td>
            <td style="display: flex; gap: 8px">
              <RouterLink class="btn ghost" :to="`/app/years/${year.id}`">查看</RouterLink>
              <button class="btn danger" @click="deleteYear(year)"><Trash2 :size="16" />删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
