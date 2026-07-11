<template>
  <div class="recycle-bin">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">
          <el-icon><Delete /></el-icon>
          回收站
        </h2>
        <span class="item-count">共 {{ total }} 项</span>
      </div>
      <div class="header-right">
        <el-input
          v-model="keyword"
          placeholder="搜索文件名..."
          clearable
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          type="danger"
          :disabled="!list.length"
          @click="handleClearAll"
        >
          <el-icon><Delete /></el-icon>
          清空回收站
        </el-button>
      </div>
    </div>

    <div class="table-wrapper">
      <el-table
        :data="list"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="文件名" min-width="300">
          <template #default="{ row }">
            <div class="file-name-cell">
              <FileTypeIcon v-if="!row.is_folder && row.file_ext" :ext="row.file_ext" :size="32" />
              <el-icon v-else-if="row.is_folder" :size="32" color="oklch(0.75 0.15 85)"><Folder /></el-icon>
              <span class="file-name" :title="row.name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="120" align="right">
          <template #default="{ row }">
            {{ row.is_folder ? '-' : formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)">
              {{ formatStatus(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="删除时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleRestore(row)">
              <el-icon><RefreshRight /></el-icon>
              恢复
            </el-button>
            <el-button type="danger" link size="small" @click="handlePermanentDelete(row)">
              <el-icon><Delete /></el-icon>
              彻底删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-wrapper">
      <AppPagination
        v-model:page="page"
        v-model:size="size"
        :total="total"
        @change="loadList"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Delete, Search, RefreshRight, Folder } from '@element-plus/icons-vue'
import FileTypeIcon from '@/components/FileTypeIcon.vue'
import AppPagination from '@/components/AppPagination.vue'
import {
  getRecycleBinList,
  restoreFromRecycleBin,
  permanentDelete,
  clearRecycleBin,
} from '@/api/knowledge'
import type { KnowledgeBaseResponse } from '@/types/api'

const loading = ref(false)
const list = ref<KnowledgeBaseResponse[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(30)
const keyword = ref('')

let searchTimer: ReturnType<typeof setTimeout> | null = null

function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadList()
  }, 300)
}

async function loadList() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: size.value }
    if (keyword.value) params.keyword = keyword.value
    console.log('[RecycleBin] 请求参数:', params)
    const res = await getRecycleBinList(params)
    console.log('[RecycleBin] 响应:', res)
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e: any) {
    console.error('[RecycleBin] 错误:', e)
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleRestore(row: KnowledgeBaseResponse) {
  await ElMessageBox.confirm(`确定恢复「${row.name}」吗？`, '确认恢复', { type: 'info' })
  await restoreFromRecycleBin(row.id)
  ElMessage.success('恢复成功')
  loadList()
}

async function handlePermanentDelete(row: KnowledgeBaseResponse) {
  await ElMessageBox.confirm(
    `确定彻底删除「${row.name}」吗？此操作不可恢复！`,
    '确认彻底删除',
    { type: 'warning' }
  )
  await permanentDelete(row.id)
  ElMessage.success('删除成功')
  loadList()
}

async function handleClearAll() {
  await ElMessageBox.confirm(
    `确定清空回收站吗？共 ${list.value.length} 项将被彻底删除，此操作不可恢复！`,
    '确认清空',
    { type: 'warning' }
  )
  await clearRecycleBin()
  ElMessage.success('回收站已清空')
  loadList()
}

function formatFileSize(bytes?: number | null): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0, size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return `${size.toFixed(1)} ${units[i]}`
}

function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatStatus(status?: string): string {
  const map: Record<string, string> = {
    uploaded: '已上传',
    pending: '待处理',
    parsing: '解析中',
    parsed: '已解析',
    completed: '已完成',
    failed: '失败',
  }
  return map[status || ''] || status || '-'
}

function getStatusType(status?: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    completed: 'success',
    parsed: 'success',
    parsing: 'warning',
    pending: 'info',
    failed: 'danger',
    uploaded: '',
  }
  return map[status || ''] || ''
}

// 监听路由变化，每次进入页面都刷新数据
const route = useRoute()

onMounted(() => loadList())

// 从其他页面切回来时刷新
watch(() => route.path, (newPath) => {
  if (newPath === '/knowledge/recycle-bin') {
    loadList()
  }
})
</script>

<style scoped>
.recycle-bin {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 240px;
}

.table-wrapper {
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
}
</style>
