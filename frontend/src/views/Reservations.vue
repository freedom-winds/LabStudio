<script setup>
import { Check, Trash2, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { formatDate } from '../data/formatters'

const reservations = ref([])
const form = ref({
  start_time: '2024-05-24T15:00:00+08:00',
  end_time: '2024-05-24T17:00:00+08:00',
  purpose: 'XRD 表征测试',
  participants_note: '3 名成员参与',
})

async function load() {
  reservations.value = (await http.get('/api/reservations')).items
}

async function submit() {
  await http.post('/api/reservations', form.value)
  await load()
}

async function approve(item, status) {
  await http.post(`/api/reservations/${item.id}/approve`, { status })
  await load()
}

async function remove(item) {
  if (!window.confirm(`确认删除预约「${item.purpose}」？`)) return
  await http.delete(`/api/reservations/${item.id}`)
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>实验室预约</h1>
        <p>学生提交使用申请，任一教师同意即通过，两位教师均拒绝才拒绝。</p>
      </div>
    </div>
    <section class="reservation-grid">
      <article class="card form-card">
        <h3>提交预约申请</h3>
        <div class="form-grid">
          <div class="field"><label>开始时间</label><input v-model="form.start_time" class="input" /></div>
          <div class="field"><label>结束时间</label><input v-model="form.end_time" class="input" /></div>
          <div class="field"><label>用途说明</label><textarea v-model="form.purpose" class="textarea" /></div>
          <div class="field"><label>参与人员说明</label><textarea v-model="form.participants_note" class="textarea" /></div>
          <button class="btn primary" @click="submit">提交预约</button>
        </div>
      </article>
      <article class="card pad">
        <div class="section-title">
          <div><h3>实验室日程</h3><p>2024 年 5 月 20 日 - 5 月 26 日</p></div>
        </div>
        <div class="calendar-grid">
          <div></div><div>周一</div><div>周二</div><div>周三</div><div>周四</div><div>周五</div><div>周六</div><div>周日</div>
          <div>09:00</div><div></div><div><div class="event">材料表征实验</div></div><div></div><div><div class="event" style="color: var(--warning); background: var(--warning-soft)">新材料合成实验</div></div><div></div><div></div><div></div>
          <div>14:00</div><div></div><div></div><div><div class="event" style="color: var(--success); background: var(--success-soft)">电化学性能测试</div></div><div></div><div><div class="event">结构分析实验</div></div><div></div><div></div>
        </div>
      </article>
      <aside class="card pad">
        <h3>审批规则说明</h3>
        <div class="timeline-list">
          <div class="timeline-item"><span class="dot" style="background: var(--success)"></span><span>任一教师同意即通过</span><Check color="#059669" /></div>
          <div class="timeline-item"><span class="dot" style="background: var(--danger)"></span><span>两位教师均拒绝才拒绝</span><X color="#dc2626" /></div>
        </div>
      </aside>
    </section>
    <section class="card table-card" style="margin-top: 24px">
      <table class="table">
        <thead><tr><th>预约时间</th><th>用途</th><th>申请人</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="item in reservations" :key="item.id">
            <td>{{ formatDate(item.start_time) }} ~ {{ formatDate(item.end_time) }}</td>
            <td>{{ item.purpose }}</td>
            <td>{{ item.applicant_id }}</td>
            <td><StatusBadge :value="item.final_status" /></td>
            <td style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
              <button class="btn ghost" @click="approve(item, 'approved')">同意</button>
              <button class="btn outline" @click="approve(item, 'rejected')">拒绝</button>
              <button class="btn danger" @click="remove(item)"><Trash2 :size="16" />删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
