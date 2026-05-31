<script setup>
import { Download, Send, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import { http } from '../api/client'
import { authState } from '../stores/auth'
import { formatDate } from '../data/formatters'

const route = useRoute()
const router = useRouter()
const chats = ref([])
const activeChatId = ref(null)
const messages = ref([])
const content = ref('')

const activeChat = computed(() => chats.value.find((item) => item.id === activeChatId.value))

async function loadChats() {
  chats.value = await http.get('/api/chats')
  const queryChatId = Number(route.query.chat_id)
  if (queryChatId && chats.value.some((item) => item.id === queryChatId)) {
    activeChatId.value = queryChatId
  } else if (!activeChatId.value && chats.value[0]) {
    activeChatId.value = chats.value[0].id
  } else if (activeChatId.value && !chats.value.some((item) => item.id === activeChatId.value)) {
    activeChatId.value = chats.value[0]?.id || null
  }
  await loadMessages()
}

async function loadMessages() {
  if (!activeChatId.value) {
    messages.value = []
    return
  }
  messages.value = await http.get(`/api/chats/${activeChatId.value}/messages`)
}

async function send() {
  if (!content.value.trim() || !activeChatId.value) return
  await http.post(`/api/chats/${activeChatId.value}/messages`, { content: content.value })
  content.value = ''
  await loadMessages()
}

async function deleteChat() {
  if (!activeChat.value) return
  if (!window.confirm(`确认删除会话「${activeChat.value.title}」？`)) return
  await http.delete(`/api/chats/${activeChat.value.id}`)
  activeChatId.value = null
  messages.value = []
  await router.replace('/app/chats')
  await loadChats()
}

watch(() => route.query.chat_id, loadChats)
onMounted(loadChats)
</script>

<template>
  <AppShell>
    <section class="card chat-layout">
      <aside class="conversation-list">
        <h3>消息中心</h3>
        <div class="tabs" style="margin-bottom: 18px">
          <button class="tab active">私聊</button>
          <button class="tab">年度群聊</button>
          <button class="tab">队伍群聊</button>
          <button class="tab">实验群聊</button>
        </div>
        <button
          v-for="chat in chats"
          :key="chat.id"
          class="conversation"
          :class="{ active: chat.id === activeChatId }"
          @click="activeChatId = chat.id; loadMessages()"
        >
          <span class="avatar">{{ chat.title.slice(0, 1) }}</span>
          <span style="text-align: left">
            <strong style="color: var(--text)">{{ chat.title }}</strong>
            <br />
            <small>{{ chat.latest_message?.content || '暂无消息' }}</small>
          </span>
          <span v-if="chat.unread_count" class="badge danger">{{ chat.unread_count }}</span>
        </button>
      </aside>
      <section style="display: grid; grid-template-rows: auto 1fr auto; min-height: 680px">
        <header style="display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 20px 28px; border-bottom: 1px solid var(--line)">
          <strong style="color: var(--text); font-size: 18px">{{ activeChat?.title || '选择会话' }}</strong>
          <button v-if="activeChat" class="btn danger" @click="deleteChat"><Trash2 :size="16" />删除会话</button>
        </header>
        <div class="messages">
          <div v-for="message in messages" :key="message.id" class="message-row" :class="{ mine: message.sender_id === authState.user?.id }">
            <span v-if="message.sender_id !== authState.user?.id" class="avatar">{{ message.sender_id }}</span>
            <div class="bubble">
              <span v-if="message.is_recalled">该消息已撤回</span>
              <template v-else>
                <span>{{ message.content }}</span>
                <a v-if="message.attachment_file_id" class="btn ghost" :href="`/api/chats/files/${message.attachment_file_id}/download`">
                  <Download :size="14" />下载附件
                </a>
              </template>
              <div style="margin-top: 6px; color: var(--faint); font-size: 12px">{{ formatDate(message.sent_at) }}</div>
            </div>
          </div>
        </div>
        <footer class="composer">
          <input v-model="content" class="input" placeholder="输入消息，Enter 发送" @keydown.enter.prevent="send" />
          <button class="btn primary" @click="send"><Send :size="18" />发送</button>
        </footer>
      </section>
    </section>
  </AppShell>
</template>
