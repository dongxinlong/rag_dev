<template>
  <div class="page-container page-fill">
    <div class="page-header">
      <h2>用户管理</h2>
    </div>

    <!-- 搜索栏 -->
    <div class="card" style="margin-bottom: var(--space-xl)">
      <el-form :inline="true">
        <el-form-item label="搜索">
          <el-input
            v-model="keyword"
            placeholder="用户名 / 邮箱 / 昵称"
            clearable
            @keyup.enter="loadData"
            style="width: 280px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="keyword = ''; loadData()">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column label="" width="60">
          <template #default="{ row }">
            <el-avatar :size="36" class="user-avatar">
              <img v-if="row.avatar" :src="row.avatar" alt="头像" />
              <span v-else>{{ (row.nickname || row.username)?.[0] || 'U' }}</span>
            </el-avatar>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="is_admin" label="角色" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'danger' : 'info'" size="small">
              {{ row.is_admin ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              type="warning"
              link
              size="small"
              @click="handleToggle(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              :disabled="row.is_admin"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <AppPagination
        :total="total"
        v-model:page="currentPage"
        v-model:size="pageSize"
        @change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, deleteUser, toggleUserActive } from '@/api/system'
import type { UserResponse } from '@/types/api'

const users = ref<UserResponse[]>([])
const total = ref(0)
const loading = ref(false)
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(30)

async function loadData() {
  loading.value = true
  try {
    const res = await listUsers({ page: currentPage.value, size: pageSize.value, keyword: keyword.value || undefined })
    users.value = res.items || []
    total.value = (res as any).total || 0
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function handleToggle(user: UserResponse) {
  const action = user.is_active ? '禁用' : '启用'
  await ElMessageBox.confirm(`确定${action}用户「${user.username}」吗？`, '确认', {
    type: 'warning',
  })
  await toggleUserActive(user.id)
  ElMessage.success(`${action}成功`)
  loadData()
}

async function handleDelete(user: UserResponse) {
  await ElMessageBox.confirm(`确定删除用户「${user.username}」吗？`, '确认删除', {
    type: 'warning',
  })
  await deleteUser(user.id)
  ElMessage.success('删除成功')
  loadData()
}

function formatDateTime(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(loadData)
</script>
