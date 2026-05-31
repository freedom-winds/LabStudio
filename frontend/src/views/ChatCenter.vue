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
const activeType = ref('private')
const messages = ref([])
const content = ref('')

const chatTypes = [
  ['private', '私聊'],
  ['year', '年度群聊'],
  ['team', '队伍群聊'],
  ['experiment', '实验群聊'],
]
const activeChat = computed(() => chats.value.find((item) => item.id === activeChatId.value))
const filteredChats = computed(() => chats.value.filter((item) => item.chat_type === activeType.value))

async function loadChats() {
  chats.value = await http.get('/api/chats')
  const queryChatId = Number(route.query.chat_id)
  const queryChat = chats.value.find((item) => item.id === queryChatId)
  if (queryChat) {
    activeType.value = queryChat.chat_type
    activeChatId.value = queryChat.id
  } else if (activeChatId.value && chats.value.some((item) => item.id === activeChatId.value)) {
    activeType.value = activeChat.value?.chat_type || activeType.value
  } else {
    activeChatId.value = filteredChats.value[0]?.id || null
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

async function switchType(type) {
  activeType.value = type
  activeChatId.value = filteredChats.value[0]?.id || null
  await router.replace('/app/chats')
  await loadMessages()
}

async function selectChat(chat) {
  activeType.value = chat.chat_type
  activeChatId.value = chat.id
  await router.replace(`/app/chats?chat_id=${chat.id}`)
  await loadMessages()
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
          <button
            v-for="[type, label] in chatTypes"
            :key="type"
            class="tab"
            :class="{ active: activeType === type }"
            @click="switchType(type)"
          >
            {{ label }}
          </button>
        </div>
        <button
          v-for="chat in filteredChats"
          :key="chat.id"
          class="conversation"
          :class="{ active: chat.id === activeChatId }"
          @click="selectChat(chat)"
        >
          <span class="avatar">{{ chat.title.slice(0, 1) }}</span>
          <span style="text-align: left">
            <strong style="color: var(--text)">{{ chat.title }}</strong>
            <br />
            <small>{{ chat.latest_message?.content || '暂无消息' }}</small>
          </span>
          <span v-if="chat.unread_count" class="badge danger">{{ chat.unread_count }}</span>
        </button>
        <div v-if="!filteredChats.length" style="color: var(--muted); padding: 16px">暂无聊天</div>
      </aside>
      <section style="display: grid; grid-template-rows: auto 1fr auto; min-height: 680px">
        <header style="display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 20px 28px; border-bottom: 1px solid var(--line)">
          <strong style="color: var(--text); font-size: 18px">{{ activeChat?.title || '暂无聊天' }}</strong>
          <button v-if="activeChat" class="btn danger" @click="deleteChat"><Trash2 :size="16" />删除会话</button>
        </header>
        <div class="messages">
          <div v-if="!activeChat" style="color: var(--muted); padding: 24px">暂无聊天</div>
          <div v-else-if="!messages.length" style="color: var(--muted); padding: 24px">暂无聊天</div>
          <div v-for="message in messages" :key="message.id" class="message-row" :class="{ mine: message.sender_id === authState.user?.id }">
            <span v-if="message.sender_id !== authState.user?.id" class="avatar">{{ message.sender?.real_name?.slice(0, 1) || '?' }}</span>
            <div class="bubble">
              <div v-if="message.sender_id !== authState.user?.id" style="margin-bottom: 4px; color: var(--faint); font-size: 12px">
                {{ message.sender?.real_name || '未知用户' }}
              </div>
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
