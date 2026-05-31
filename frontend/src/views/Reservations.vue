<script setup>
import { Check, Trash2, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { http } from '../api/client'
import { formatDate } from '../data/formatters'
import { authState } from '../stores/auth'

const reservations = ref([])
const error = ref('')
const submitting = ref(false)
const form = ref({
  start_time: '',
  end_time: '',
  purpose: '',
  participants_note: '',
})
const isTeacher = computed(() => ['teacher', 'admin'].includes(authState.user?.account_type))

async function load() {
  reservations.value = (await http.get('/api/reservations')).items
}

async function submit() {
  error.value = ''
  if (!form.value.start_time || !form.value.end_time || !form.value.purpose.trim()) {
    error.value = '请填写开始时间、结束时间和用途说明。'
    return
  }
  submitting.value = true
  try {
    await http.post('/api/reservations', form.value)
    form.value = { start_time: '', end_time: '', purpose: '', participants_note: '' }
    await load()
  } catch (err) {
    error.value = err.message || '提交预约失败'
  } finally {
    submitting.value = false
  }
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
        <p>按真实预约记录依次展示，教师审批后状态立即更新为已通过或已拒绝。</p>
      </div>
    </div>
    <section class="reservation-grid" style="grid-template-columns: minmax(320px, 420px) 1fr">
      <article class="card form-card">
        <h3>提交预约申请</h3>
        <div class="form-grid">
          <div class="field"><label>开始时间</label><input v-model="form.start_time" type="datetime-local" class="input" /></div>
          <div class="field"><label>结束时间</label><input v-model="form.end_time" type="datetime-local" class="input" /></div>
          <div class="field"><label>用途说明</label><textarea v-model="form.purpose" class="textarea" /></div>
          <div class="field"><label>参与人员说明</label><textarea v-model="form.participants_note" class="textarea" /></div>
          <p v-if="error" class="error" style="margin: 0">{{ error }}</p>
          <button class="btn primary" :disabled="submitting" @click="submit">提交预约</button>
        </div>
      </article>
      <article class="card pad">
        <h3>审批规则说明</h3>
        <div class="timeline-list">
          <div class="timeline-item"><span class="dot" style="background: var(--success)"></span><span>教师同意后状态为已通过</span><Check color="#059669" /></div>
          <div class="timeline-item"><span class="dot" style="background: var(--danger)"></span><span>教师拒绝后状态为已拒绝</span><X color="#dc2626" /></div>
        </div>
      </article>
    </section>
    <section class="card table-card" style="margin-top: 24px">
      <table class="table">
        <thead><tr><th>预约时间</th><th>用途</th><th>申请人</th><th>审批记录</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="item in reservations" :key="item.id">
            <td>{{ formatDate(item.start_time) }} ~ {{ formatDate(item.end_time) }}</td>
            <td>
              <strong style="color: var(--text)">{{ item.purpose }}</strong>
              <div v-if="item.participants_note" style="color: var(--muted); margin-top: 6px">{{ item.participants_note }}</div>
            </td>
            <td>{{ item.applicant?.real_name || item.applicant_id }}</td>
            <td>
              <div v-if="item.approvals?.length" class="timeline-list" style="gap: 8px">
                <div v-for="approval in item.approvals" :key="approval.id" style="display: flex; gap: 8px; align-items: center">
                  <span>{{ approval.teacher?.real_name || approval.teacher_id }}</span>
                  <StatusBadge :value="approval.status" />
                </div>
              </div>
              <span v-else style="color: var(--muted)">暂无审批记录</span>
            </td>
            <td><StatusBadge :value="item.final_status" /></td>
            <td style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
              <button v-if="isTeacher && item.final_status === 'pending'" class="btn ghost" @click="approve(item, 'approved')">同意</button>
              <button v-if="isTeacher && item.final_status === 'pending'" class="btn outline" @click="approve(item, 'rejected')">拒绝</button>
              <button class="btn danger" @click="remove(item)"><Trash2 :size="16" />删除</button>
            </td>
          </tr>
          <tr v-if="!reservations.length">
            <td colspan="6" style="color: var(--muted)">暂无预约记录。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
