<template>
  <div class="page-container">
    <div class="page-header">
      <h2>个人中心</h2>
    </div>

    <!-- 顶部：头像卡片 -->
    <div class="card profile-top-card">
      <div class="profile-top-inner">
        <div class="avatar-area">
          <el-upload
            class="avatar-uploader"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleAvatarChange"
            accept="image/*"
          >
            <el-avatar :size="80" class="user-avatar">
              <img v-if="avatarUrl" :src="avatarUrl" alt="头像" />
              <span v-else>{{ user?.nickname?.[0] || user?.username?.[0] || 'U' }}</span>
            </el-avatar>
            <div class="avatar-overlay">
              <el-icon :size="20"><Camera /></el-icon>
              <span>更换头像</span>
            </div>
          </el-upload>
          <div class="user-meta">
            <h3>{{ user?.nickname || user?.username }}</h3>
            <el-tag :type="user?.is_admin ? 'danger' : 'info'" size="small">
              {{ user?.is_admin ? '管理员' : '普通用户' }}
            </el-tag>
          </div>
        </div>
        <el-descriptions :column="3" class="info-row">
          <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ user?.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ formatDateTime(user?.created_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <!-- 编辑资料 -->
    <div class="card">
      <h3 class="card-title">编辑资料</h3>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="80px" style="max-width: 480px">
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="formData.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 修改密码 -->
    <div class="card">
      <h3 class="card-title">修改密码</h3>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px" style="max-width: 480px">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="8-20位，含大小写+数字+特殊字符" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="warning" :loading="changingPwd" @click="handleChangePassword">修改密码</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { updateUserInfo, uploadAvatar } from '@/api/system'
import { changePassword } from '@/api/auth'

const authStore = useAuthStore()
const avatarUrl = ref('')

// 直接用 store 的 user，保证和 header 同步
const user = computed(() => authStore.user)

// 资料表单
const formRef = ref<FormInstance>()
const saving = ref(false)
const formData = reactive({ nickname: '', email: '' })
const formRules: FormRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
}

// 密码表单
const pwdFormRef = ref<FormInstance>()
const changingPwd = ref(false)
const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$/
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

function validateNewPassword(_rule: any, value: string, callback: any) {
  if (!value) callback(new Error('请输入新密码'))
  else if (!passwordRegex.test(value)) callback(new Error('8-20位，需包含大小写字母、数字和特殊字符'))
  else callback()
}
function validateConfirm(_rule: any, value: string, callback: any) {
  if (value !== pwdForm.new_password) callback(new Error('两次输入密码不一致'))
  else callback()
}
const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, validator: validateNewPassword, trigger: 'blur' }],
  confirm_password: [{ required: true, validator: validateConfirm, trigger: 'blur' }],
}

async function loadUser() {
  if (user.value) {
    formData.nickname = user.value.nickname || ''
    formData.email = user.value.email || ''
    avatarUrl.value = user.value.avatar || ''
  }
}

/** 上传头像 */
async function handleAvatarChange(file: UploadFile) {
  if (!file.raw) return
  try {
    // 预览本地图片
    const reader = new FileReader()
    reader.onload = (e) => {
      avatarUrl.value = e.target?.result as string
    }
    reader.readAsDataURL(file.raw)

    await uploadAvatar(file.raw)
    ElMessage.success('头像上传成功')
    // 同步到 store
    if (user.value) {
      authStore.setUserInfo({ ...user.value, avatar: avatarUrl.value })
    }
  } catch {
    ElMessage.error('头像上传失败')
  }
}

/** 保存资料 */
async function handleSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const res = await updateUserInfo({ nickname: formData.nickname, email: formData.email })
      // 合并更新，保留 avatar 等字段
      if (user.value) {
        authStore.setUserInfo({ ...user.value, ...res.data })
      }
      ElMessage.success('保存成功')
    } catch { ElMessage.error('保存失败') }
    finally { saving.value = false }
  })
}

/** 修改密码 */
async function handleChangePassword() {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    changingPwd.value = true
    try {
      await changePassword({ old_password: pwdForm.old_password, new_password: pwdForm.new_password })
      ElMessage.success('密码修改成功，请重新登录')
      authStore.logout()
    } catch { ElMessage.error('密码修改失败') }
    finally { changingPwd.value = false }
  })
}

function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(loadUser)
</script>

<style lang="scss" scoped>
.profile-top-card {
  margin-bottom: 20px;
}

.profile-top-inner {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.avatar-area {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar-uploader {
  position: relative;
  cursor: pointer;

  .user-avatar {
    background: var(--color-primary);
    color: white;
    font-size: 28px;
    font-weight: 700;
    border: 3px solid white;
    box-shadow: 0 2px 8px oklch(0 0 0 / 0.1);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .avatar-overlay {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: oklch(0 0 0 / 0.4);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
    gap: 2px;
    opacity: 0;
    transition: opacity var(--duration-fast);
  }

  &:hover .avatar-overlay {
    opacity: 1;
  }
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;

  h3 {
    font-size: var(--text-xl);
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
  }
}

.info-row {
  :deep(.el-descriptions__label) {
    font-weight: 500;
  }
}

.card + .card {
  margin-top: 24px;
}

.card-title {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 20px;
}
</style>
