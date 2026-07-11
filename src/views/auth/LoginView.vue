<template>
  <div class="login-page">
    <!-- 流星雨（全局背景） -->
    <div class="meteor-shower">
      <div class="meteor"></div>
      <div class="meteor"></div>
      <div class="meteor"></div>
      <div class="meteor"></div>
      <div class="meteor"></div>
      <div class="meteor"></div>
      <div class="meteor"></div>
      <div class="meteor"></div>
    </div>

    <!-- 星星背景 -->
    <div class="star-field">
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
      <div class="star"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <!-- 左侧品牌区 -->
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

        <!-- 底部装饰插画区 -->
        <div class="brand-illustration">
          <svg viewBox="0 0 300 120" fill="none" xmlns="http://www.w3.org/2000/svg" class="illustration-svg">
            <!-- 桌子 -->
            <rect x="40" y="70" width="220" height="4" rx="2" fill="oklch(0.40 0.040 250 / 0.15)" />
            <rect x="60" y="74" width="4" height="30" rx="2" fill="oklch(0.40 0.040 250 / 0.12)" />
            <rect x="236" y="74" width="4" height="30" rx="2" fill="oklch(0.40 0.040 250 / 0.12)" />
            <!-- 人物1 -->
            <circle cx="100" cy="50" r="8" fill="oklch(0.50 0.100 250 / 0.2)" />
            <rect x="94" y="58" width="12" height="14" rx="4" fill="oklch(0.50 0.100 250 / 0.15)" />
            <!-- 人物2 -->
            <circle cx="160" cy="48" r="8" fill="oklch(0.72 0.120 85 / 0.2)" />
            <rect x="154" y="56" width="12" height="16" rx="4" fill="oklch(0.72 0.120 85 / 0.12)" />
            <!-- 人物3 -->
            <circle cx="210" cy="52" r="8" fill="oklch(0.50 0.100 250 / 0.15)" />
            <rect x="204" y="60" width="12" height="12" rx="4" fill="oklch(0.50 0.100 250 / 0.10)" />
            <!-- 屏幕 -->
            <rect x="88" y="38" width="24" height="16" rx="3" stroke="oklch(0.50 0.100 250 / 0.25)" stroke-width="1.5" fill="none" />
            <rect x="148" y="36" width="24" height="16" rx="3" stroke="oklch(0.72 0.120 85 / 0.25)" stroke-width="1.5" fill="none" />
            <rect x="198" y="40" width="24" height="16" rx="3" stroke="oklch(0.50 0.100 250 / 0.2)" stroke-width="1.5" fill="none" />
            <!-- 装饰点 -->
            <circle cx="50" cy="30" r="2" fill="oklch(0.50 0.100 250 / 0.15)" />
            <circle cx="260" cy="40" r="3" fill="oklch(0.72 0.120 85 / 0.1)" />
            <circle cx="280" cy="20" r="2" fill="oklch(0.50 0.100 250 / 0.12)" />
          </svg>
        </div>
      </div>

      <!-- 右侧表单区 -->
      <div class="card-form">
        <div class="form-container">
          <div class="form-header">
            <h2>欢迎回来</h2>
            <p>请输入账号密码登录系统</p>
          </div>

          <el-form
            ref="formRef"
            :model="loginForm"
            :rules="loginRules"
            size="large"
            @keyup.enter="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="用户名或邮箱"
                prefix-icon="User"
                clearable
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="密码"
                prefix-icon="Lock"
                show-password
                clearable
              />
            </el-form-item>

            <el-form-item>
              <div class="form-options">
                <el-checkbox v-model="rememberMe">记住我</el-checkbox>
                <router-link to="/forgot-password" class="forgot-link">忘记密码?</router-link>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                class="login-btn"
                :loading="loading"
                @click="handleLogin"
              >
                {{ loading ? '登录中...' : '登 录' }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-divider">
            <span>或</span>
          </div>

          <el-button class="register-btn" @click="$router.push('/register')">
            新注册账号
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const rememberMe = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.login(loginForm.username, loginForm.password)
      ElMessage.success('登录成功')

      // 跳转到来源页或首页
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    } catch (error: any) {
      ElMessage.error(error?.message || '登录失败，请检查用户名和密码')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style lang="scss" scoped>
@use './auth-shared.scss';
</style>
