<script setup>
import { onMounted, ref } from 'vue'
import PublicShell from '../components/layout/PublicShell.vue'
import { http } from '../api/client'

const honors = ref([])

onMounted(async () => {
  honors.value = await http.get('/api/public/honor-members').catch(() => [])
})
</script>

<template>
  <PublicShell>
    <section class="container" style="padding: 54px 0 70px">
      <div class="page-title">
        <div>
          <h1>荣誉墙</h1>
          <p>公开展示实验室成员、历史毕业成员与重要贡献者的成就。</p>
        </div>
        <RouterLink class="btn outline" to="/">返回首页</RouterLink>
      </div>
      <div class="card-grid three">
        <article v-for="member in honors" :key="member.id" class="card pad">
          <div style="display: flex; gap: 18px; align-items: center">
            <span class="avatar large">{{ member.name.slice(0, 1) }}</span>
            <div>
              <h3 style="margin: 0 0 10px; color: var(--text)">{{ member.name }}</h3>
              <span class="badge primary">荣誉成员</span>
            </div>
          </div>
          <p style="margin-top: 18px; color: var(--muted); line-height: 1.8">{{ member.description }}</p>
        </article>
      </div>
    </section>
  </PublicShell>
</template>
