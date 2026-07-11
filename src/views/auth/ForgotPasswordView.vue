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

    <!-- 忘记密码卡片 -->
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
      </div>

      <div class="card-form">
        <div class="form-container">
          <div class="form-header">
            <h2>忘记密码</h2>
            <p>请输入用户名，联系管理员重置密码</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" size="large">
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" class="login-btn" @click="handleSubmit">
                提交申请
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-footer-link">
            <router-link to="/login">← 返回登录</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const formRef = ref<FormInstance>()
const form = reactive({ username: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
}

function handleSubmit() {
  formRef.value?.validate((valid) => {
    if (valid) {
      ElMessage.info('密码重置申请已提交，请联系管理员处理')
    }
  })
}
</script>

<style lang="scss" scoped>
@import './auth-shared.scss';
</style>
