<template>
  <div class="page-container">
    <div class="page-header">
      <h2>仪表盘</h2>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.key">
        <div class="stat-card">
          <div class="stat-icon" :style="{ background: stat.bgColor }">
            <el-icon :size="24" :color="stat.color">
              <component :is="stat.icon" />
            </el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stat.value }}</span>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <div class="card">
          <h3 class="card-title">快捷操作</h3>
          <div class="quick-actions">
            <div
              v-for="action in quickActions"
              :key="action.path"
              class="action-item"
              @click="$router.push(action.path)"
            >
              <div class="action-icon" :style="{ background: action.bgColor }">
                <el-icon :size="20" :color="action.color">
                  <component :is="action.icon" />
                </el-icon>
              </div>
              <div class="action-info">
                <span class="action-name">{{ action.name }}</span>
                <span class="action-desc">{{ action.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card">
          <h3 class="card-title">最近对话</h3>
          <div class="recent-chat-list" v-if="recentChats.length">
            <div
              v-for="chat in recentChats"
              :key="chat.id"
              class="chat-item"
              @click="$router.push('/chat')"
            >
              <el-icon><ChatDotRound /></el-icon>
              <span class="chat-title text-ellipsis">{{ chat.title }}</span>
              <span class="chat-time">{{ formatTime(chat.updated_at) }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无对话记录" :image-size="80" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listChats } from '@/api/chat'
import type { ChatResponse } from '@/types/api'

const stats = ref([
  { key: 'knowledge', label: '知识库', value: '0', icon: 'Collection', color: 'oklch(0.50 0.100 250)', bgColor: 'oklch(0.50 0.100 250 / 0.1)' },
  { key: 'document', label: '文档总数', value: '0', icon: 'Document', color: 'oklch(0.72 0.120 85)', bgColor: 'oklch(0.72 0.120 85 / 0.1)' },
  { key: 'chat', label: '对话数', value: '0', icon: 'ChatDotRound', color: 'oklch(0.62 0.150 155)', bgColor: 'oklch(0.62 0.150 155 / 0.1)' },
  { key: 'user', label: '用户数', value: '0', icon: 'User', color: 'oklch(0.58 0.180 25)', bgColor: 'oklch(0.58 0.180 25 / 0.1)' },
])

const quickActions = ref([
  { name: '新建知识库', desc: '创建新的知识库', icon: 'FolderAdd', path: '/knowledge', color: 'oklch(0.50 0.100 250)', bgColor: 'oklch(0.50 0.100 250 / 0.1)' },
  { name: '开始对话', desc: '与 AI 进行问答', icon: 'ChatDotRound', path: '/chat', color: 'oklch(0.72 0.120 85)', bgColor: 'oklch(0.72 0.120 85 / 0.1)' },
  { name: '用户管理', desc: '管理系统用户', icon: 'User', path: '/system/user', color: 'oklch(0.62 0.150 155)', bgColor: 'oklch(0.62 0.150 155 / 0.1)' },
  { name: '角色管理', desc: '配置系统角色', icon: 'Lock', path: '/system/role', color: 'oklch(0.58 0.180 25)', bgColor: 'oklch(0.58 0.180 25 / 0.1)' },
])

const recentChats = ref<ChatResponse[]>([])

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  return d.toLocaleDateString('zh-CN')
}

onMounted(async () => {
  try {
    const res = await listChats({ page: 1, size: 5 })
    recentChats.value = res.items || []
  } catch {
    // 忽略加载错误
  }
})
</script>

<style lang="scss" scoped>
.stat-row {
  margin-bottom: var(--space-xl);
}

.stat-card {
  background: var(--color-bg-elevated);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  padding: var(--space-xl);
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  transition: box-shadow var(--duration-normal) var(--ease-out);

  &:hover {
    box-shadow: var(--shadow-md);
  }
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.card-title {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-lg);
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-md);
}

.action-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast);

  &:hover {
    background: var(--color-bg-hover);
  }
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-info {
  display: flex;
  flex-direction: column;

  .action-name {
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--color-text-primary);
  }

  .action-desc {
    font-size: var(--text-xs);
    color: var(--color-text-secondary);
  }
}

.recent-chat-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chat-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast);

  &:hover {
    background: var(--color-bg-hover);
  }

  .el-icon {
    color: var(--color-text-placeholder);
    flex-shrink: 0;
  }

  .chat-title {
    flex: 1;
    font-size: var(--text-sm);
    color: var(--color-text-regular);
  }

  .chat-time {
    font-size: var(--text-xs);
    color: var(--color-text-placeholder);
    flex-shrink: 0;
  }
}
</style>
