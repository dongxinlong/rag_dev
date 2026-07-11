<template>
  <div class="page-container">
    <div class="page-header">
      <h2>知识库管理</h2>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        新建知识库
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="card" style="margin-bottom: var(--space-xl)">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="知识库名称">
          <el-input
            v-model="searchForm.name"
            placeholder="搜索知识库"
            clearable
            @keyup.enter="loadData"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetSearch">
            <el-icon><RefreshRight /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 知识库列表 -->
    <div class="kb-grid">
      <div
        v-for="cat in categories"
        :key="cat.id"
        class="kb-card"
        @click="goToDetail(cat.id)"
      >
        <div class="kb-card-header">
          <div class="kb-icon">
            <el-icon :size="24">
              <component :is="cat.icon || 'Collection'" />
            </el-icon>
          </div>
          <el-dropdown
            v-if="isCreator(cat)"
            trigger="click"
            @command="(cmd: string) => handleCommand(cmd, cat)"
            @click.stop
          >
            <div class="more-btn" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <el-icon><Edit /></el-icon> 编辑
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon><Delete /></el-icon> 删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <h3 class="kb-name text-ellipsis">{{ cat.name }}</h3>
        <p class="kb-desc text-ellipsis">{{ cat.description || '暂无描述' }}</p>

        <div class="kb-meta">
          <span class="meta-item" v-if="cat.creator_name">
            <el-icon><User /></el-icon>
            {{ cat.creator_name }}
          </span>
          <span class="meta-item">
            <el-icon><Timer /></el-icon>
            {{ formatDate(cat.created_at) }}
          </span>
        </div>
      </div>

      <!-- 新建卡片 -->
      <div class="kb-card kb-card-new" @click="showCreateDialog">
        <el-icon :size="32" color="var(--color-text-placeholder)"><Plus /></el-icon>
        <span>新建知识库</span>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑知识库' : '新建知识库'"
      width="520px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入知识库名称" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述（选填）"
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="图标">
          <div class="icon-picker">
            <div
              v-for="icon in iconOptions"
              :key="icon"
              class="icon-option"
              :class="{ active: formData.icon === icon }"
              @click="formData.icon = formData.icon === icon ? '' : icon"
            >
              <el-icon :size="18"><component :is="icon" /></el-icon>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  listCategories,
  createCategory,
  updateCategory,
  deleteCategory,
} from '@/api/knowledge'
import type { CategoryResponse } from '@/types/api'

const router = useRouter()
const authStore = useAuthStore()
const categories = ref<CategoryResponse[]>([])

/** 判断是否是创建人（admin 管理所有，普通用户只能操作自己创建的） */
function isCreator(cat: CategoryResponse): boolean {
  if (authStore.user?.is_admin) return true
  return String(cat.creator_id) === String(authStore.user?.id)
}
const loading = ref(false)

const searchForm = reactive({ name: '' })

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(0)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()

const formData = reactive({
  name: '',
  description: '',
  icon: '',
})

/** 可选图标列表 */
const iconOptions = [
  'Collection', 'Document', 'Notebook', 'Reading',
  'ChatDotRound', 'ChatLineSquare', 'Voice',
  'Picture', 'VideoCamera', 'Microphone',
  'Folder', 'FolderOpened', 'Files',
  'Link', 'Share', 'Star',
  'Bookmark', 'Tag', 'PriceTag',
  'Flag', 'Location', 'Map',
  'Clock', 'Timer', 'AlarmClock',
  'Trophy', 'Medal', 'MagicStick',
  'Cpu', 'Monitor', 'DataLine',
  'TrendCharts', 'PieChart', 'DataBoard',
  'Reading', 'Edit', 'EditPen',
  'Promotion', 'Opportunity', 'Discount',
]

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度 2-50 个字符', trigger: 'blur' },
  ],
}

async function loadData() {
  loading.value = true
  try {
    const res = await listCategories({
      page: 1,
      size: 100,
      keyword: searchForm.name || undefined,
    })
    categories.value = (res as any).items || res.data || []
  } catch {
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchForm.name = ''
  loadData()
}

function showCreateDialog() {
  isEdit.value = false
  editId.value = 0
  formData.name = ''
  formData.description = ''
  formData.icon = ''
  dialogVisible.value = true
}

function handleCommand(cmd: string, cat: CategoryResponse) {
  if (cmd === 'edit') {
    isEdit.value = true
    editId.value = cat.id
    formData.name = cat.name
    formData.description = cat.description || ''
    formData.icon = cat.icon || ''
    dialogVisible.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(`确定要删除知识库「${cat.name}」吗？`, '确认删除', {
      type: 'warning',
    }).then(async () => {
      await deleteCategory(cat.id)
      ElMessage.success('删除成功')
      loadData()
    }).catch(() => {})
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      if (isEdit.value) {
        await updateCategory(editId.value, {
          name: formData.name,
          description: formData.description || undefined,
          icon: formData.icon || undefined,
        })
        ElMessage.success('更新成功')
      } else {
        await createCategory({
          name: formData.name,
          description: formData.description || undefined,
          icon: formData.icon || undefined,
        })
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadData()
    } catch {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    } finally {
      submitLoading.value = false
    }
  })
}

function goToDetail(categoryId: number) {
  router.push({ path: '/knowledge/detail', query: { category_id: categoryId } })
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay}天前`

  // 超过7天显示具体日期
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')

  if (year === now.getFullYear()) {
    return `${month}-${day} ${hour}:${min}`
  }
  return `${year}-${month}-${day} ${hour}:${min}`
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.kb-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);

  &:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--color-primary-lighter);
  }

  &-new {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    border-style: dashed;
    color: var(--color-text-placeholder);
    min-height: 180px;

    &:hover {
      border-color: var(--color-primary);
      color: var(--color-primary);
    }

    span {
      font-size: var(--text-sm);
    }
  }
}

.kb-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.kb-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-lighter);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.more-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-placeholder);
  transition: all var(--duration-fast);

  &:hover {
    background: var(--color-bg-hover);
    color: var(--color-text-regular);
  }
}

.kb-name {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.kb-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
}

.kb-meta {
  display: flex;
  gap: var(--space-lg);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-placeholder);

  .el-icon {
    font-size: 14px;
  }
}

// 图标选择器
.icon-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-width: 400px;
}

.icon-option {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all var(--duration-fast);
  color: var(--color-text-secondary);

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background: var(--color-primary-lighter);
  }

  &.active {
    border-color: var(--color-primary);
    background: var(--color-primary);
    color: white;
  }
}

</style>
