<template>
  <div class="not-found">
    <div class="not-found-content">
      <h1>404</h1>
      <p>页面不存在</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
}
.not-found-content {
  text-align: center;
}
.not-found-content h1 {
  font-size: 6rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1;
  margin-bottom: 16px;
}
.not-found-content p {
  color: var(--color-text-secondary);
  margin-bottom: 32px;
  font-size: 1.125rem;
}
</style>
