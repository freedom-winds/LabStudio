<script setup>
import { Download, Send, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import UserAvatar from '../components/ui/UserAvatar.vue'
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
const filteredChats = computed(() =>
  chats.value
    .filter((item) => item.chat_type === activeType.value)
    .sort((left, right) => chatLastActivity(right) - chatLastActivity(left)),
)

function chatLastActivity(chat) {
  const value = chat.last_activity_at || chat.latest_message?.sent_at || chat.updated_at || chat.created_at
  return value ? new Date(value).getTime() || 0 : 0
}

function chatTypeLabel(type) {
  return chatTypes.find(([value]) => value === type)?.[1] || '聊天'
}

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
  await loadChats()
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
        <div class="conversation-list-header">
          <h3>消息中心</h3>
        </div>
        <div class="chat-type-tabs" role="tablist" aria-label="聊天类型">
          <button
            v-for="[type, label] in chatTypes"
            :key="type"
            class="chat-type-tab"
            :class="{ active: activeType === type }"
            @click="switchType(type)"
          >
            {{ label }}
          </button>
        </div>
        <div class="conversation-scroll">
          <button
            v-for="chat in filteredChats"
            :key="chat.id"
            class="conversation"
            :class="{ active: chat.id === activeChatId }"
            @click="selectChat(chat)"
          >
            <UserAvatar :user="chat.private_peer" :name="chat.title" :size="38" />
            <span class="conversation-body">
              <span class="conversation-title-row">
                <strong>{{ chat.title }}</strong>
                <small v-if="chat.latest_message">{{ formatDate(chat.latest_message.sent_at) }}</small>
              </span>
              <span class="conversation-preview">{{ chat.latest_message?.content || '暂无消息' }}</span>
            </span>
            <span v-if="chat.unread_count" class="badge danger">{{ chat.unread_count }}</span>
          </button>
          <div v-if="!filteredChats.length" class="chat-empty">暂无聊天</div>
        </div>
      </aside>
      <section class="chat-panel">
        <header class="chat-header">
          <div class="chat-title">
            <strong>{{ activeChat?.title || '暂无聊天' }}</strong>
            <span>{{ activeChat ? chatTypeLabel(activeChat.chat_type) : '请选择一个会话' }}</span>
          </div>
          <button v-if="activeChat" class="btn danger" @click="deleteChat"><Trash2 :size="16" />删除会话</button>
        </header>
        <div class="messages">
          <div v-if="!activeChat" class="chat-empty">暂无聊天</div>
          <div v-else-if="!messages.length" class="chat-empty">暂无聊天</div>
          <div v-for="message in messages" :key="message.id" class="message-row" :class="{ mine: message.sender_id === authState.user?.id }">
            <UserAvatar v-if="message.sender_id !== authState.user?.id" :user="message.sender" :size="38" />
            <div class="bubble">
              <div v-if="message.sender_id !== authState.user?.id" class="message-sender">
                {{ message.sender?.real_name || '未知用户' }}
              </div>
              <span v-if="message.is_recalled">该消息已撤回</span>
              <template v-else>
                <span>{{ message.content }}</span>
                <a v-if="message.attachment_file_id" class="btn ghost" :href="`/api/chats/files/${message.attachment_file_id}/download`">
                  <Download :size="14" />下载附件
                </a>
              </template>
              <div class="message-time">{{ formatDate(message.sent_at) }}</div>
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
