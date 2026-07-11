<template>
  <div class="page-container page-fill">
    <div class="page-header">
      <div class="header-left">
        <el-button text @click="$router.push('/knowledge/list')">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2>{{ categoryName || '知识库详情' }}</h2>
      </div>
      <div class="header-actions">
        <el-button @click="loadFiles" :loading="loading">
          <el-icon><RefreshRight /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="showUploadDialog">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
        <el-button @click="showCreateFolderDialog">
          <el-icon><FolderAdd /></el-icon>
          新建文件夹
        </el-button>
      </div>
    </div>

    <!-- 文件列表 -->
    <div class="card">
      <!-- 面包屑导航 -->
      <div class="breadcrumb-bar" v-if="breadcrumbs.length > 1">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item
            v-for="(item, idx) in breadcrumbs"
            :key="item.id"
          >
            <span
              v-if="idx < breadcrumbs.length - 1"
              class="breadcrumb-link"
              @click="navigateTo(item)"
            >
              {{ item.name }}
            </span>
            <span v-else class="breadcrumb-current">{{ item.name }}</span>
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <!-- 搜索栏 -->
      <div class="file-search-bar" v-if="files.length > 0 || searchKeyword">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索当前目录文件..."
          clearable
          prefix-icon="Search"
          style="width: 300px"
          @keyup.enter="handleSearch"
          @clear="handleClearSearch"
        />
        <el-button type="primary" @click="handleSearch" :loading="isSearching">
          搜索
        </el-button>
      </div>

      <el-table
        :data="files"
        v-loading="loading"
        stripe
        @row-dblclick="handleRowDblClick"
        @row-contextmenu="handleContextMenu"
      >
        <el-table-column label="名称" min-width="280">
          <template #default="{ row }">
            <div class="file-name" @click="handleRowClick(row)">
              <FileTypeIcon v-if="!row.is_folder && row.file_ext" :ext="row.file_ext" :size="32" />
              <el-icon v-else :size="20" class="folder-icon" style="color: #E6A23C">
                <Folder />
              </el-icon>
              <span class="file-name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="120">
          <template #default="{ row }">
            {{ row.creator_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">
            {{ row.is_folder ? '-' : formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              v-if="!row.is_folder"
              :type="['parsed', 'completed'].includes(row.status) ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'uploaded' ? 'info' : 'warning'"
              size="small"
            >
              {{ statusMap[row.status] || row.status || '未知' }}
            </el-tag>
            <span v-else class="text-secondary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at || row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.is_folder" type="primary" link size="small" @click="handleDownloadFile(row)">
              下载
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && files.length === 0" description="暂无文件，点击上方按钮上传" />

      <AppPagination
        :total="total"
        v-model:page="currentPage"
        v-model:size="pageSize"
        @change="loadFiles"
      />
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传文件" width="520px" destroy-on-close>
      <div class="upload-tabs">
        <div
          class="upload-tab"
          :class="{ active: uploadMode === 'file' }"
          @click="uploadMode = 'file'"
        >
          <el-icon><Document /></el-icon>
          上传文件
        </div>
        <div
          class="upload-tab"
          :class="{ active: uploadMode === 'folder' }"
          @click="uploadMode = 'folder'"
        >
          <el-icon><FolderOpened /></el-icon>
          上传文件夹
        </div>
      </div>

      <!-- 文件上传 -->
      <el-upload
        v-if="uploadMode === 'file'"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="uploadFiles"
        accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls"
        multiple
      >
        <el-icon :size="40"><Upload /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 PDF、Word、TXT、Markdown、CSV、Excel</div>
        </template>
      </el-upload>

      <!-- 文件夹上传 -->
      <div v-else class="folder-upload-area">
        <input
          ref="folderInputRef"
          type="file"
          webkitdirectory
          multiple
          style="display: none"
          @change="handleFolderInputChange"
        />
        <div class="folder-upload-box" @click="folderInputRef?.click()">
          <el-icon :size="40"><FolderOpened /></el-icon>
          <div class="el-upload__text">点击选择文件夹</div>
          <div class="el-upload__tip">选择文件夹后，将自动创建目录结构并上传所有文件</div>
        </div>
        <div v-if="uploadFiles.length > 0" class="folder-file-list">
          <div class="folder-file-count">
            已选择 <strong>{{ uploadFiles.length }}</strong> 个文件
          </div>
        </div>
      </div>

      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-progress">
        <el-progress :percentage="uploadProgress" :status="uploadProgress === 100 ? 'success' : undefined" />
        <span class="progress-text">{{ uploadingText }}</span>
      </div>

      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="uploadFiles.length === 0" @click="handleUpload">
          上传 ({{ uploadFiles.length }})
        </el-button>
      </template>
    </el-dialog>

    <!-- 新建文件夹对话框 -->
    <el-dialog v-model="folderDialogVisible" title="新建文件夹" width="400px" destroy-on-close>
      <el-form :model="{ folderName }" :rules="{ folderName: [{ required: true, message: '请输入文件夹名称', trigger: 'blur' }] }" ref="folderFormRef">
        <el-form-item prop="folderName">
          <el-input v-model="folderName" placeholder="请输入文件夹名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateFolder">创建</el-button>
      </template>
    </el-dialog>

    <!-- 文件预览 -->
    <FilePreview
      v-model="previewVisible"
      :file-name="previewFile.name"
      :file-url="previewFile.url"
      :file-size="previewFile.size"
      :ext="previewFile.ext"
    />

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div
        v-if="contextMenuVisible"
        class="context-menu"
        :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
        @click="contextMenuVisible = false"
      >
        <div class="context-menu-item" @click="handleContextAction('rename')">
          <el-icon><Edit /></el-icon>
          <span>重命名</span>
        </div>
        <div class="context-menu-item" @click="handleContextAction('move')">
          <el-icon><Rank /></el-icon>
          <span>移动到</span>
        </div>
        <div class="context-menu-item" @click="handleContextAction('copy')">
          <el-icon><CopyDocument /></el-icon>
          <span>复制到</span>
        </div>
        <div class="context-menu-divider" />
        <div class="context-menu-item danger" @click="handleContextAction('delete')">
          <el-icon><Delete /></el-icon>
          <span>删除</span>
        </div>
      </div>
    </Teleport>

    <!-- 文件夹树选择器 -->
    <FolderTreeSelect
      v-model="folderTreeVisible"
      :category-id="categoryId"
      :title="folderTreeTitle"
      @confirm="handleMoveCopyConfirm"
    />

    <!-- 重命名对话框 -->
    <el-dialog v-model="renameVisible" title="重命名" width="400px" destroy-on-close>
      <el-form ref="renameFormRef" :model="{ name: renameValue }" :rules="{ name: [{ required: true, message: '请输入名称', trigger: 'blur' }] }">
        <el-form-item prop="name">
          <el-input v-model="renameValue" placeholder="请输入新名称" autofocus @keyup.enter="handleRenameConfirm" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" :loading="renameLoading" @click="handleRenameConfirm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import FileTypeIcon from '@/components/FileTypeIcon.vue'
import FolderTreeSelect from '@/components/FolderTreeSelect.vue'
import FilePreview from '@/components/FilePreview.vue'
import {
  listCategories,
  listKnowledgeBases,
  uploadFile,
  deleteKnowledgeBase,
  createFolder,
  getNavigation,
  getPreviewUrl,
  searchFiles,
  moveFile,
  copyFile,
  renameFile,
  type NavigationItem,
} from '@/api/knowledge'
import type { KnowledgeBaseResponse } from '@/types/api'

const route = useRoute()
const categoryId = computed(() => {
  const val = route.query.category_id
  return val ? String(val) : ''
})

const categoryName = ref('')
const files = ref<KnowledgeBaseResponse[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(30)
const loading = ref(false)
const currentParentId = ref('')
const breadcrumbs = ref<NavigationItem[]>([])

// 上传
const uploadDialogVisible = ref(false)
const uploadFiles = ref<UploadFile[]>([])
const uploading = ref(false)
const uploadMode = ref<'file' | 'folder'>('file')
const uploadProgress = ref(0)
const uploadingText = ref('')
const folderInputRef = ref<HTMLInputElement>()
const MAX_FILE_COUNT = 500 // 单次最多上传文件数

// 搜索
const searchKeyword = ref('')
const isSearching = ref(false)

// 右键菜单
const contextMenuVisible = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuTarget = ref<KnowledgeBaseResponse | null>(null)

// 重命名
const renameVisible = ref(false)
const renameTarget = ref<KnowledgeBaseResponse | null>(null)
const renameValue = ref('')
const renameLoading = ref(false)
const renameFormRef = ref()

// 移动/复制
const folderTreeVisible = ref(false)
const folderTreeTitle = ref('')
const folderTreeAction = ref<'move' | 'copy'>('move')

// 新建文件夹
const folderDialogVisible = ref(false)
const folderName = ref('')
const creating = ref(false)
const folderFormRef = ref()

const statusMap: Record<string, string> = {
  uploaded: '上传完成',
  pending: '待解析',
  parsing: '解析中',
  parsed: '已解析',
  completed: '解析完成',
  failed: '解析失败',
}

/** 加载分类信息 */
async function loadCategoryInfo() {
  if (!categoryId.value) return
  try {
    const res = await listCategories({ page: 1, size: 100 })
    const items = (res as any).items || []
    const cat = items.find((c: any) => c.id === categoryId.value)
    if (cat) categoryName.value = cat.name
  } catch {
    // 忽略
  }
}

/** 加载文件列表 */
async function loadFiles() {
  if (!categoryId.value) return
  loading.value = true
  try {
    const params: any = {
      category_id: categoryId.value,
      page: currentPage.value,
      size: pageSize.value,
    }
    if (currentParentId.value) params.parent_id = currentParentId.value
    const res = await listKnowledgeBases(params)
    files.value = (res as any).items || []
    total.value = (res as any).total || 0
  } catch {
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

/** 搜索文件 */
async function handleSearch() {
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    loadFiles()
    return
  }
  isSearching.value = true
  try {
    const res = await searchFiles({
      keyword,
      category_id: categoryId.value,
      parent_id: currentParentId.value || undefined,
    })
    files.value = (res as any).items || []
    total.value = (res as any).total || 0
  } catch {
    ElMessage.error('搜索失败')
  } finally {
    isSearching.value = false
  }
}

/** 清空搜索 */
function handleClearSearch() {
  searchKeyword.value = ''
  loadFiles()
}

/** 加载面包屑导航 */
async function loadBreadcrumbs() {
  const targetId = currentParentId.value || categoryId.value
  if (!targetId) return
  try {
    const res = await getNavigation(targetId)
    breadcrumbs.value = res.data || []
  } catch {
    breadcrumbs.value = []
  }
}

/** 右键菜单 */
function handleContextMenu(row: KnowledgeBaseResponse, _column: any, event: MouseEvent) {
  event.preventDefault()
  contextMenuTarget.value = row
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  contextMenuVisible.value = true
}

function handleContextAction(action: string) {
  const target = contextMenuTarget.value
  if (!target) return

  if (action === 'rename') {
    renameTarget.value = target
    renameValue.value = target.name
    renameVisible.value = true
  } else if (action === 'move') {
    folderTreeTitle.value = `移动「${target.name}」到...`
    folderTreeAction.value = 'move'
    folderTreeVisible.value = true
  } else if (action === 'copy') {
    folderTreeTitle.value = `复制「${target.name}」到...`
    folderTreeAction.value = 'copy'
    folderTreeVisible.value = true
  } else if (action === 'delete') {
    handleDelete(target)
  }

  contextMenuVisible.value = false
}

/** 重命名确认 */
async function handleRenameConfirm() {
  if (!renameTarget.value || !renameValue.value.trim()) return
  if (renameValue.value === renameTarget.value.name) {
    renameVisible.value = false
    return
  }

  renameLoading.value = true
  try {
    await renameFile(renameTarget.value.id, renameValue.value.trim())
    ElMessage.success(`已重命名为「${renameValue.value}」`)
    renameVisible.value = false
    loadFiles()
  } catch {
    ElMessage.error('重命名失败')
  } finally {
    renameLoading.value = false
  }
}

/** 移动/复制确认 */
async function handleMoveCopyConfirm(targetId: string) {
  const target = contextMenuTarget.value
  if (!target) return

  // 'root' = 根目录，传空字符串给后端
  const actualTargetId = targetId === 'root' ? '' : targetId

  try {
    if (folderTreeAction.value === 'move') {
      await moveFile(target.id, actualTargetId)
      ElMessage.success(`已移动「${target.name}」`)
    } else {
      await copyFile(target.id, actualTargetId)
      ElMessage.success(`已复制「${target.name}」`)
    }
    loadFiles()
    loadBreadcrumbs()
  } catch {
    ElMessage.error(folderTreeAction.value === 'move' ? '移动失败' : '复制失败')
  }
}

/** 面包屑路径 */
function navigateTo(item: NavigationItem) {
  if (item.id === '0') {
    currentParentId.value = ''
  } else {
    currentParentId.value = item.id
  }
  currentPage.value = 1
  loadFiles()
  loadBreadcrumbs()
}

/** 点击文件行 */
/** 支持预览的文件格式（后端转换） */
const previewableExts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv', 'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp']

// 预览状态
const previewVisible = ref(false)
const previewFile = ref<{ name: string; url: string; size?: number; ext: string }>({
  name: '', url: '', ext: '',
})

async function handleRowClick(row: KnowledgeBaseResponse) {
  if (row.is_folder) {
    currentParentId.value = row.id
    currentPage.value = 1
    loadFiles()
    loadBreadcrumbs()
  } else {
    // 文件：调预览接口
    try {
      const res = await getPreviewUrl(row.id)
      previewFile.value = {
        name: res.data.name,
        url: res.data.url,
        size: row.file_size || undefined,
        ext: res.data.ext,
      }
      // 打开预览（office/pdf/image 会自动新标签页，md/txt/csv 弹窗）
      previewVisible.value = true
    } catch {
      ElMessage.warning('该文件类型不支持预览')
    }
  }
}

function handleRowDblClick(row: KnowledgeBaseResponse) {
  handleRowClick(row)
}

/** 下载文件（用原始文件名） */
async function handleDownloadFile(row: KnowledgeBaseResponse) {
  try {
    const res = await getPreviewUrl(row.id)
    const response = await fetch(res.data.url)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败')
  }
}

/** 上传文件 */
function showUploadDialog() {
  uploadFiles.value = []
  uploadDialogVisible.value = true
}

function handleFileChange(file: UploadFile) {
  if (!uploadFiles.value.find(f => f.name === file.name)) {
    uploadFiles.value.push(file)
  }
}

/** 文件夹选择变化 */
function handleFolderChange(file: UploadFile) {
  if (!uploadFiles.value.find(f => f.name === file.name && f.webkitRelativePath === (file as any).webkitRelativePath)) {
    uploadFiles.value.push(file)
  }
}

/** 文件夹 input change */
function handleFolderInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return

  const files = Array.from(input.files)
  if (files.length > MAX_FILE_COUNT) {
    ElMessage.warning(`单次最多上传 ${MAX_FILE_COUNT} 个文件，当前选择 ${files.length} 个`)
    input.value = ''
    return
  }

  for (const file of files) {
    const uploadFile: UploadFile = {
      name: file.name,
      raw: file,
      status: 'ready',
      uid: Date.now() + Math.random(),
    }
    ;(uploadFile as any).webkitRelativePath = (file as any).webkitRelativePath
    uploadFiles.value.push(uploadFile)
  }
  input.value = ''
}

/** 延迟函数 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/** 带重试的请求（处理 429 限流） */
async function withRetry<T>(fn: () => Promise<T>, maxRetries = 2): Promise<T> {
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn()
    } catch (error: any) {
      // 429: 限流，解析等待时间并重试
      if (error?.response?.status === 429 && i < maxRetries) {
        const message = error?.response?.data?.message || ''
        // 从 "请 0.8 秒后重试" 中提取时间
        const match = message.match(/(\d+(?:\.\d+)?)\s*秒/)
        const waitMs = match ? parseFloat(match[1]) * 1000 : 2000
        console.warn(`[限流] 第 ${i + 1} 次重试，等待 ${waitMs}ms`)
        await sleep(waitMs)
        continue
      }
      throw error
    }
  }
  throw new Error('重试次数已用尽')
}

/** 并发控制函数 */
async function concurrencyLimit<T>(tasks: (() => Promise<T>)[], limit: number): Promise<T[]> {
  const results: T[] = []
  const executing = new Set<Promise<T>>()

  for (const task of tasks) {
    const p = task().then(r => {
      executing.delete(p)
      return r
    })
    executing.add(p)
    results.push(p)

    if (executing.size >= limit) {
      await Promise.race(executing)
    }
  }

  return Promise.all(results)
}

/** 解析文件夹结构，返回排序后的目录列表 */
function parseFolderStructure(files: UploadFile[]): string[] {
  const folders = new Set<string>()

  for (const file of files) {
    const relativePath = (file.raw as any)?.webkitRelativePath || ''
    if (!relativePath) continue

    const parts = relativePath.split('/')
    // 收集所有中间目录（排除最后一个文件名）
    for (let i = 1; i < parts.length; i++) {
      folders.add(parts.slice(0, i).join('/'))
    }
  }

  // 按深度排序（父目录在前）
  return Array.from(folders).sort((a, b) => a.split('/').length - b.split('/').length)
}

async function handleUpload() {
  if (uploadMode.value === 'folder') {
    await handleFolderUpload()
  } else {
    await handleFileUpload()
  }
}

/** 普通文件上传 */
async function handleFileUpload() {
  uploading.value = true
  uploadProgress.value = 0
  let successCount = 0
  let failCount = 0
  const total = uploadFiles.value.length
  const MAX_FAIL = Math.min(total * 0.3, 50)
  const interval = Number(import.meta.env.VITE_UPLOAD_INTERVAL) || 180

  const tasks = uploadFiles.value
    .filter(f => f.raw)
    .map((file, idx) => async () => {
      if (failCount >= MAX_FAIL) return
      uploadingText.value = `正在上传 ${idx + 1}/${total}：${file.name}`
      try {
        await withRetry(() => uploadFile(file.raw!, categoryId.value, currentParentId.value || undefined))
        successCount++
      } catch {
        failCount++
        if (failCount <= 10) ElMessage.error(`上传 ${file.name} 失败`)
      }
      uploadProgress.value = Math.round(((idx + 1) / total) * 100)
      // 控制速率，不超过桶填充率
      await sleep(interval)
    })

  await concurrencyLimit(tasks, Number(import.meta.env.VITE_UPLOAD_CONCURRENCY) || 5)
  uploading.value = false
  uploadDialogVisible.value = false
  uploadMode.value = 'file'
  uploadFiles.value = []

  if (successCount > 0) {
    ElMessage.success(`成功上传 ${successCount} 个文件`)
    loadFiles()
  }
}

/** 文件夹上传 */
async function handleFolderUpload() {
  const folderStructure = parseFolderStructure(uploadFiles.value)
  if (folderStructure.length === 0 && uploadFiles.value.length === 0) return

  uploading.value = true
  uploadProgress.value = 0
  uploadingText.value = '正在创建目录结构...'

  // 1. 按层级创建文件夹
  const folderMap = new Map<string, string>()
  let folderFailCount = 0

  for (const folderPath of folderStructure) {
    const parts = folderPath.split('/')
    const folderName = parts[parts.length - 1]
    const parentPath = parts.slice(0, -1).join('/')
    const parentId = folderMap.get(parentPath) || currentParentId.value || undefined

    try {
      const res = await withRetry(() => createFolder(folderName, categoryId.value, parentId))
      folderMap.set(folderPath, res.data.id)
    } catch {
      folderFailCount++
      ElMessage.error(`创建文件夹 ${folderName} 失败`)
      if (folderFailCount >= 5) {
        ElMessage.error('文件夹创建失败过多，已停止')
        break
      }
    }
    await sleep(200)
  }

  // 2. 并发上传文件
  const filesToUpload = uploadFiles.value.filter(f => f.raw)
  let successCount = 0
  let failCount = 0
  const total = filesToUpload.length
  const MAX_FAIL = Math.min(total * 0.3, 50)
  const interval = Number(import.meta.env.VITE_UPLOAD_INTERVAL) || 180

  const tasks = filesToUpload.map((file, idx) => async () => {
    if (failCount >= MAX_FAIL) return

    const relativePath = (file.raw as any).webkitRelativePath || ''
    const dir = relativePath.substring(0, relativePath.lastIndexOf('/'))
    const parentId = folderMap.get(dir) || currentParentId.value || undefined

    uploadingText.value = `正在上传 ${idx + 1}/${total}：${file.name}`
    try {
      await withRetry(() => uploadFile(file.raw!, categoryId.value, parentId))
      successCount++
    } catch {
      failCount++
      if (failCount <= 10) ElMessage.error(`上传 ${file.name} 失败`)
    }
    uploadProgress.value = Math.round(((idx + 1) / total) * 100)
    // 控制速率
    await sleep(interval)
  })

  await concurrencyLimit(tasks, Number(import.meta.env.VITE_UPLOAD_CONCURRENCY) || 5)
  uploading.value = false
  uploadDialogVisible.value = false
  uploadMode.value = 'file'
  uploadFiles.value = []

  // 汇总结果
  if (failCount >= MAX_FAIL) {
    ElMessage.warning(`上传中断：成功 ${successCount} 个，失败 ${failCount}+ 个（已停止）`)
  } else if (successCount > 0) {
    ElMessage.success(`成功上传 ${successCount} 个文件${failCount > 0 ? `，失败 ${failCount} 个` : ''}`)
  }
  if (successCount > 0) {
    loadFiles()
    loadBreadcrumbs()
  }
}

/** 新建文件夹 */
function showCreateFolderDialog() {
  folderName.value = ''
  folderDialogVisible.value = true
}

async function handleCreateFolder() {
  if (!folderName.value.trim()) return
  creating.value = true
  try {
    await withRetry(() => createFolder(folderName.value, categoryId.value, currentParentId.value || undefined))
    ElMessage.success('创建成功')
    folderDialogVisible.value = false
    loadFiles()
  } catch {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

/** 删除 */
async function handleDelete(row: KnowledgeBaseResponse) {
  await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '确认删除', { type: 'warning' })
  await deleteKnowledgeBase(row.id)
  ElMessage.success('删除成功')
  loadFiles()
}

/** 工具函数 */
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

onMounted(() => {
  loadCategoryInfo()
  loadFiles()
  loadBreadcrumbs()

  // 点击空白处关闭右键菜单
  document.addEventListener('click', () => {
    contextMenuVisible.value = false
  })
})
</script>

<style lang="scss" scoped>
.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
}

.breadcrumb-bar {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border-light);
}

.breadcrumb-link {
  color: var(--color-primary);
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}

.breadcrumb-current {
  color: var(--color-text-primary);
  font-weight: 500;
}

// 搜索栏
.file-search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

// 右键菜单
.context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 4px 0;
  min-width: 160px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--duration-fast);

  &:hover {
    background: var(--color-bg-hover);
  }

  &.danger {
    color: var(--color-danger);

    &:hover {
      background: oklch(0.60 0.190 25 / 0.08);
    }
  }
}

.context-menu-divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 4px 0;
}

// 上传模式切换
.upload-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.upload-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all var(--duration-fast);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &.active {
    border-color: var(--color-primary);
    background: var(--color-primary-lighter);
    color: var(--color-primary);
    font-weight: 500;
  }
}

// 上传进度
.upload-progress {
  margin-top: 16px;
  padding: 12px;
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.progress-text {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-top: 4px;
  display: block;
}

// 文件夹上传区域
.folder-upload-area {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--duration-fast);
  cursor: pointer;

  &:hover {
    border-color: var(--color-primary);
  }
}

.folder-upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.folder-file-list {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-page);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.folder-file-count {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);

  strong {
    color: var(--color-primary);
  }
}

.file-name {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  cursor: pointer;

  &:hover .file-name-text {
    color: var(--color-primary);
  }
}

.file-icon,
.folder-icon {
  flex-shrink: 0;
}

.file-name-text {
  color: var(--color-text-primary);
  transition: color var(--duration-fast);
}

.text-secondary {
  color: var(--color-text-placeholder);
  font-size: var(--text-sm);
}
</style>
