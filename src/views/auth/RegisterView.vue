<template>
  <div class="login-page">
    <!-- 流星雨 -->
    <div class="meteor-shower">
      <div class="meteor"></div><div class="meteor"></div><div class="meteor"></div>
      <div class="meteor"></div><div class="meteor"></div><div class="meteor"></div>
      <div class="meteor"></div><div class="meteor"></div>
    </div>
    <div class="star-field">
      <div class="star"></div><div class="star"></div><div class="star"></div>
      <div class="star"></div><div class="star"></div><div class="star"></div>
      <div class="star"></div><div class="star"></div><div class="star"></div>
      <div class="star"></div>
    </div>

    <!-- 注册卡片 -->
    <div class="login-card">
      <div class="card-brand">
        <div class="brand-content">
          <div class="brand-icon">
            <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="12" fill="oklch(0.50 0.100 250)" />
              <path d="M14 34V18l10-6 10 6v16l-10 6-10-6z" stroke="white" stroke-width="2" fill="none" />
              <path d="M14 18l10 6 10-6M24 24v16" stroke="white" stroke-width="2" />
            </svg>
          </div>
          <h1>RAG 知识库系统</h1>
          <p class="brand-desc">企业级智能知识管理平台</p>
          <div class="brand-features">
            <div class="feature-item">
              <el-icon><Collection /></el-icon>
              <span>智能文档解析与向量检索</span>
            </div>
            <div class="feature-item">
              <el-icon><ChatDotRound /></el-icon>
              <span>基于知识库的 AI 对话</span>
            </div>
            <div class="feature-item">
              <el-icon><Lock /></el-icon>
              <span>企业级 RBAC 权限体系</span>
            </div>
          </div>
        </div>
        <div class="brand-illustration">
          <svg viewBox="0 0 300 120" fill="none" xmlns="http://www.w3.org/2000/svg" class="illustration-svg">
            <rect x="40" y="70" width="220" height="4" rx="2" fill="oklch(0.40 0.040 250 / 0.15)" />
            <rect x="60" y="74" width="4" height="30" rx="2" fill="oklch(0.40 0.040 250 / 0.12)" />
            <rect x="236" y="74" width="4" height="30" rx="2" fill="oklch(0.40 0.040 250 / 0.12)" />
            <circle cx="100" cy="50" r="8" fill="oklch(0.50 0.100 250 / 0.2)" />
            <rect x="94" y="58" width="12" height="14" rx="4" fill="oklch(0.50 0.100 250 / 0.15)" />
            <circle cx="160" cy="48" r="8" fill="oklch(0.72 0.120 85 / 0.2)" />
            <rect x="154" y="56" width="12" height="16" rx="4" fill="oklch(0.72 0.120 85 / 0.12)" />
            <circle cx="210" cy="52" r="8" fill="oklch(0.50 0.100 250 / 0.15)" />
            <rect x="204" y="60" width="12" height="12" rx="4" fill="oklch(0.50 0.100 250 / 0.10)" />
          </svg>
        </div>
      </div>

      <div class="card-form">
        <div class="form-container">
          <div class="form-header">
            <h2>注册账号</h2>
            <p>创建一个新账号</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleSubmit">
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="3-20位，字母开头，字母数字下划线" prefix-icon="User" clearable />
            </el-form-item>
            <el-form-item prop="email">
              <el-input v-model="form.email" placeholder="邮箱" prefix-icon="Message" clearable />
            </el-form-item>
            <el-form-item prop="nickname">
              <el-input v-model="form.nickname" placeholder="昵称（选填）" prefix-icon="UserFilled" clearable />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="form.password" type="password" placeholder="8-20位，含大小写+数字+特殊字符" prefix-icon="Lock" show-password clearable />
            </el-form-item>
            <el-form-item prop="confirmPassword">
              <el-input v-model="form.confirmPassword" type="password" placeholder="确认密码" prefix-icon="Lock" show-password clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" class="login-btn" :loading="loading" @click="handleSubmit">
                {{ loading ? '注册中...' : '注 册' }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-footer-link">
            已有账号？<router-link to="/login">去登录</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { register } from '@/api/auth'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  nickname: '',
  password: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const usernameRegex = /^[a-zA-Z][a-zA-Z0-9_]{2,19}$/
const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$/

function validateUsername(_rule: any, value: string, callback: any) {
  if (!value) {
    callback(new Error('请输入用户名'))
  } else if (!usernameRegex.test(value)) {
    callback(new Error('3-20位，以字母开头，只能包含字母、数字和下划线'))
  } else {
    callback()
  }
}

function validatePassword(_rule: any, value: string, callback: any) {
  if (!value) {
    callback(new Error('请输入密码'))
  } else if (!passwordRegex.test(value)) {
    callback(new Error('8-20位，需包含大小写字母、数字和特殊字符(@$!%*?&)'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  username: [
    { required: true, validator: validateUsername, trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  nickname: [{ required: false }],
  password: [
    { required: true, validator: validatePassword, trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await register({
        username: form.username,
        email: form.email,
        nickname: form.nickname || undefined,
        password: form.password,
      })
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } catch {
      ElMessage.error('注册失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style lang="scss" scoped>
@use './auth-shared.scss';
</style>
