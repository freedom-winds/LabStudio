<script setup>
import { Download, Trash2, Upload, Wrench } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { http } from '../api/client'
import { fileSize, formatDate } from '../data/formatters'

const tools = ref([])

async function load() {
  tools.value = (await http.get('/api/toolbox')).items
}

async function upload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  form.append('name', file.name)
  form.append('version', '1.0.0')
  form.append('description', '实验室内部工具')
  await http.post('/api/toolbox', form)
  event.target.value = ''
  await load()
}

async function remove(tool) {
  if (!window.confirm(`确认删除工具「${tool.name}」？`)) return
  await http.delete(`/api/toolbox/${tool.id}`, { reason: '前端删除' })
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-title">
      <div>
        <h1>工具箱</h1>
        <p>实验室内部工具下载与维护。</p>
      </div>
      <label class="btn primary"><Upload :size="18" />上传工具<input hidden type="file" @change="upload" /></label>
    </div>
    <section class="card-grid three">
      <article v-for="tool in tools" :key="tool.id" class="card pad">
        <span class="stat-icon"><Wrench :size="22" /></span>
        <h3 style="margin-top: 18px">{{ tool.name }}</h3>
        <p style="color: var(--muted); line-height: 1.7">{{ tool.description || '暂无简介' }}</p>
        <div class="badge-row">
          <span class="badge primary">v{{ tool.version }}</span>
          <span class="badge">{{ fileSize(tool.file_size) }}</span>
          <span class="badge">{{ formatDate(tool.updated_at) }}</span>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px">
          <a class="btn outline" :href="`/api/toolbox/${tool.id}/download`"><Download :size="16" />下载工具</a>
          <button class="btn danger" @click="remove(tool)"><Trash2 :size="16" />删除</button>
        </div>
      </article>
    </section>
  </AppShell>
</template>
