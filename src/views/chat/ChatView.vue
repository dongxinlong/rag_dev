<template>
  <div class="chat-layout">
    <!-- 左侧对话列表 -->
    <div class="chat-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleNewChat">
          <el-icon><Plus /></el-icon>
          <span v-if="!sidebarCollapsed">新建对话</span>
        </el-button>
        <el-icon
          v-if="!sidebarCollapsed"
          class="collapse-btn"
          @click="sidebarCollapsed = true"
        >
          <Fold />
        </el-icon>
        <el-icon v-else class="collapse-btn" @click="sidebarCollapsed = false">
          <Expand />
        </el-icon>
      </div>

      <el-scrollbar class="conversation-list" v-if="!sidebarCollapsed">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: currentConvId === conv.id }"
          @click="selectConversation(conv.id)"
        >
          <el-icon class="conv-icon"><ChatDotRound /></el-icon>
          <div class="conv-info">
            <span class="conv-title text-ellipsis">{{ conv.title }}</span>
            <span class="conv-meta">{{ conv.updated_at }}</span>
          </div>
        </div>

        <el-empty v-if="conversations.length === 0" description="暂无对话" :image-size="60" />
      </el-scrollbar>
    </div>

    <!-- 右侧聊天区 -->
    <div class="chat-main">
      <!-- 欢迎页 -->
      <div v-if="!currentConvId" class="chat-welcome">
        <div class="welcome-icon">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <rect width="64" height="64" rx="16" fill="oklch(0.50 0.100 250 / 0.1)" />
            <path d="M20 44V28l12-8 12 8v16l-12 8-12-8z" stroke="oklch(0.50 0.100 250)" stroke-width="2" fill="none" />
          </svg>
        </div>
        <h2>RAG 知识库助手</h2>
        <p>基于知识库的智能问答，上传文档后即可开始对话</p>
        <div class="welcome-tips">
          <div class="tip-item" v-for="tip in tips" :key="tip">
            <el-icon><ChatLineSquare /></el-icon>
            <span>{{ tip }}</span>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-else class="chat-messages" ref="messagesRef">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message"
          :class="msg.role"
        >
          <div class="message-avatar">
            <el-avatar :size="36" v-if="msg.role === 'user'" :src="authStore.user?.avatar">
              {{ authStore.user?.nickname?.[0] || 'U' }}
            </el-avatar>
            <el-avatar :size="36" v-else class="ai-avatar">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)" />
            <div v-if="msg.sources?.length" class="message-sources">
              <div class="sources-chips">
                <el-tag
                  v-for="(src, idx) in msg.sources"
                  :key="idx"
                  class="source-chip"
                  effect="plain"
                  size="small"
                >
                  <el-icon><Document /></el-icon>
                  <span class="source-name">{{ src.file_name }}</span>
                  <span class="source-score">{{ (src.similarity * 100).toFixed(0) }}%</span>
                </el-tag>
              </div>
            </div>
            <div class="message-time">{{ formatTime(msg.created_at) }}</div>
          </div>
        </div>

        <!-- 思考中 -->
        <div v-if="sending && thinking" class="message assistant">
          <div class="message-avatar">
            <el-avatar :size="36" class="ai-avatar">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="thinking-indicator">
              <div class="thinking-dot"></div>
              <div class="thinking-dot"></div>
              <div class="thinking-dot"></div>
              <span class="thinking-text">思考中...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area" v-if="currentConvId">
        <div class="input-container">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 6 }"
            placeholder="输入你的问题..."
            :disabled="sending"
            @keydown.enter.exact.prevent="handleSend"
          />
          <el-button
            type="primary"
            circle
            :icon="Promotion"
            :loading="sending"
            :disabled="!inputText.trim()"
            @click="handleSend"
            class="send-btn"
          />
        </div>
        <div class="input-tip">Enter 发送，Shift + Enter 换行</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { listChats, createChat, ragQueryStream, listMessages } from '@/api/chat'
import type { ChatResponse, MessageResponse, Source } from '@/types/api'
import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

/** 前端消息结构 */
interface LocalMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  created_at: string
}

const authStore = useAuthStore()

const conversations = ref<ChatResponse[]>([])
const currentConvId = ref<string | null>(null)
const messages = ref<LocalMessage[]>([])
const inputText = ref('')
const sending = ref(false)
const thinking = ref(false)
const sidebarCollapsed = ref(false)
const messagesRef = ref<HTMLDivElement>()

const tips = [
  '上传文档到知识库后，AI 会基于文档内容回答问题',
  '输入问题后 AI 会基于知识库进行检索回答',
  '聊天记录自动保存到服务器',
]

async function loadConversations() {
  try {
    const res = await listChats({ page: 1, size: 50 })
    conversations.value = res.items || []
  } catch {
    // 忽略
  }
}

async function handleNewChat() {
  try {
    const res = await createChat({ title: '新对话' })
    conversations.value.unshift(res.data)
    selectConversation(res.data.id)
  } catch {
    ElMessage.error('创建对话失败')
  }
}

async function selectConversation(id: string) {
  currentConvId.value = id
  messages.value = []

  // 从后端加载消息历史
  try {
    const res = await listMessages(id)
    messages.value = (res.items || []).map(msg => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      sources: msg.extra_data?.sources || [],
      created_at: msg.created_at,
    }))
  } catch {
    // 加载失败，显示空对话
  }

  scrollToBottom()
}

async function handleSend() {
  const content = inputText.value.trim()
  if (!content || sending.value || !currentConvId.value) return

  const chatId = currentConvId.value

  // 显示用户消息
  const userMsg: LocalMessage = {
    id: `user-${Date.now()}`,
    role: 'user',
    content,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  inputText.value = ''
  sending.value = true
  thinking.value = true
  scrollToBottom()

  try {
    const assistantMsg: LocalMessage = {
      id: `ai-${Date.now()}`,
      role: 'assistant',
      content: '',
      sources: [],
      created_at: new Date().toISOString(),
    }
    messages.value.push(assistantMsg)

    let answer = ''

    // 流式查询
    for await (const event of ragQueryStream(chatId, content)) {
      switch (event.type) {
        case 'content':
          if (thinking.value) thinking.value = false
          answer += event.value || ''
          assistantMsg.content = answer
          scrollToBottom()
          break
        case 'sources':
          assistantMsg.sources = event.value || []
          break
        case 'cost':
          // 成本信息，可选显示
          break
        case 'error':
          ElMessage.error(event.value || '查询出错')
          break
      }
    }

    scrollToBottom()
  } catch {
    ElMessage.error('查询失败，请检查知识库是否已上传文档')
  } finally {
    thinking.value = false
    sending.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function renderMarkdown(text: string): string {
  if (!text) return ''
  return marked.parse(text) as string
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(loadConversations)
</script>

<style lang="scss" scoped>
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.chat-sidebar {
  width: 280px;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  transition: width var(--duration-normal) var(--ease-out);
  flex-shrink: 0;

  &.collapsed {
    width: 52px;
  }
}

.sidebar-header {
  padding: var(--space-md);
  display: flex;
  gap: var(--space-sm);
  border-bottom: 1px solid var(--color-border-light);

  .new-chat-btn {
    flex: 1;
  }

  .collapse-btn {
    cursor: pointer;
    color: var(--color-text-secondary);
    padding: 8px;
    border-radius: var(--radius-md);

    &:hover {
      background: var(--color-bg-hover);
    }
  }
}

.conversation-list {
  flex: 1;
  padding: var(--space-sm);
}

.conv-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast);
  margin-bottom: 2px;

  &:hover {
    background: var(--color-bg-hover);
  }

  &.active {
    background: var(--color-primary-lighter);

    .conv-icon, .conv-title {
      color: var(--color-primary);
    }
  }
}

.conv-icon {
  color: var(--color-text-placeholder);
  flex-shrink: 0;
}

.conv-info {
  flex: 1;
  min-width: 0;

  .conv-title {
    display: block;
    font-size: var(--text-sm);
    color: var(--color-text-primary);
  }

  .conv-meta {
    font-size: var(--text-xs);
    color: var(--color-text-placeholder);
  }
}

// 聊天主区域
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl);

  h2 {
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--color-text-primary);
    margin-top: var(--space-xl);
    margin-bottom: var(--space-sm);
  }

  p {
    color: var(--color-text-secondary);
    margin-bottom: var(--space-2xl);
  }
}

.welcome-tips {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.tip-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-page);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);

  .el-icon {
    color: var(--color-primary);
    flex-shrink: 0;
  }

  span {
    font-size: var(--text-sm);
    color: var(--color-text-regular);
  }
}

// 消息列表
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xl) var(--space-3xl);
}

.message {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;

  &.user {
    flex-direction: row-reverse;

    .message-content {
      align-items: flex-end;
    }

    .message-text {
      background: var(--color-primary);
      color: white;
      border-radius: var(--radius-lg) var(--radius-sm) var(--radius-lg) var(--radius-lg);
    }
  }

  &.assistant .message-text {
    background: var(--color-bg-elevated);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg);
  }
}

.message-avatar {
  flex-shrink: 0;
}

.ai-avatar {
  background: var(--color-primary);
  color: white;
  font-size: var(--text-xs);
  font-weight: 700;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-text {
  padding: var(--space-md) var(--space-lg);
  line-height: 1.7;
  font-size: var(--text-base);
  word-break: break-word;

  :deep(pre) {
    background: oklch(0.13 0.020 260);
    color: oklch(0.90 0.010 260);
    padding: var(--space-md);
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin: var(--space-sm) 0;
    font-family: var(--font-family-mono);
    font-size: var(--text-sm);
  }

  :deep(code) {
    background: oklch(0.95 0.003 260);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-family: var(--font-family-mono);
    font-size: 0.9em;
  }

  // Markdown 样式
  :deep(p) {
    margin: 0.5em 0;
    &:first-child { margin-top: 0; }
    &:last-child { margin-bottom: 0; }
  }

  :deep(ul), :deep(ol) {
    margin: 0.5em 0;
    padding-left: 1.5em;
  }

  :deep(li) {
    margin: 0.25em 0;
  }

  :deep(blockquote) {
    border-left: 3px solid var(--color-primary);
    margin: 0.5em 0;
    padding: 0.5em 1em;
    background: oklch(0.95 0.003 260);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  }

  :deep(table) {
    border-collapse: collapse;
    margin: 0.5em 0;
    width: 100%;

    th, td {
      border: 1px solid var(--color-border-light);
      padding: 0.5em 1em;
      text-align: left;
    }

    th {
      background: var(--color-bg-page);
      font-weight: 600;
    }
  }

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    margin: 1em 0 0.5em;
    font-weight: 600;
    &:first-child { margin-top: 0; }
  }

  :deep(h1) { font-size: 1.5em; }
  :deep(h2) { font-size: 1.3em; }
  :deep(h3) { font-size: 1.1em; }
}

.message-sources {
  margin-top: var(--space-sm);
}

.sources-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;

  .el-icon {
    font-size: 14px;
  }

  .source-name {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .source-score {
    font-size: 11px;
    color: var(--color-text-placeholder);
    margin-left: 4px;
  }
}

.message-time {
  font-size: var(--text-xs);
  color: var(--color-text-placeholder);
  margin-top: 4px;
}

// 思考中指示器
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg);
}

.thinking-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: thinking 1.4s infinite;

  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}

.thinking-text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-left: 4px;
}

@keyframes thinking {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

// 输入区
.chat-input-area {
  padding: var(--space-lg) var(--space-3xl);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-elevated);
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: var(--space-sm);
  max-width: 800px;
  margin: 0 auto;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-sm) var(--space-sm) var(--space-sm) var(--space-lg);
  transition: border-color var(--duration-fast);

  &:focus-within {
    border-color: var(--color-primary);
  }

  :deep(.el-textarea__inner) {
    border: none !important;
    box-shadow: none !important;
    background: transparent;
    padding: 4px 0;
    resize: none;
  }
}

.send-btn {
  flex-shrink: 0;
}

.input-tip {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-text-placeholder);
  margin-top: var(--space-sm);
}

@media (max-width: 768px) {
  .chat-sidebar {
    display: none;
  }

  .chat-messages {
    padding: var(--space-lg);
  }

  .chat-input-area {
    padding: var(--space-md);
  }

  .message-content {
    max-width: 85%;
  }
}
</style>
