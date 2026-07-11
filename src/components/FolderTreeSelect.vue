<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="title"
    width="480px"
    destroy-on-close
  >
    <div class="folder-tree-select">
      <!-- 根目录 -->
      <div
        class="tree-item root-item"
        :class="{ active: selectedId === 'root' }"
        @click="selectedId = 'root'"
      >
        <el-icon><FolderOpened /></el-icon>
        <span>根目录</span>
      </div>

      <!-- 文件夹树 -->
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="{ label: 'name', children: 'children' }"
        node-key="id"
        highlight-current
        :expand-on-click-node="false"
        v-loading="loading"
        @current-change="handleNodeClick"
      >
        <template #default="{ node, data }">
          <div class="tree-item">
            <el-icon><Folder /></el-icon>
            <span>{{ data.name }}</span>
          </div>
        </template>
      </el-tree>

      <el-empty v-if="!loading && treeData.length === 0" description="暂无文件夹" :image-size="60" />
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleConfirm">
        确定移动到此处
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getFolderTree, type FolderTreeNode } from '@/api/knowledge'

const props = defineProps<{
  modelValue: boolean
  categoryId: string
  title?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'confirm', targetId: string): void
}>()

const treeRef = ref()
const treeData = ref<FolderTreeNode[]>([])
const loading = ref(false)
const selectedId = ref('')

watch(() => props.modelValue, async (val) => {
  if (val && props.categoryId) {
    loading.value = true
    try {
      const res = await getFolderTree(props.categoryId)
      treeData.value = res.data || []
    } catch {
      treeData.value = []
    } finally {
      loading.value = false
    }
  }
})

function handleNodeClick(data: FolderTreeNode) {
  selectedId.value = data.id
}

function handleConfirm() {
  emit('confirm', selectedId.value)
  emit('update:modelValue', false)
}
</script>

<style lang="scss" scoped>
.folder-tree-select {
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
}

.tree-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast);

  &:hover {
    background: var(--color-bg-hover);
  }

  &.active {
    background: var(--color-primary-lighter);
    color: var(--color-primary);
  }

  .el-icon {
    color: #E6A23C;
  }
}

.root-item {
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: 8px;
  padding-bottom: 12px;
}
</style>
