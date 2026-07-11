<template>
  <el-config-provider :size="appStore.size">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

// 响应式：检测设备类型
function handleResize() {
  const width = window.innerWidth
  appStore.setDevice(width < 768 ? 'mobile' : 'desktop')
}

window.addEventListener('resize', handleResize)
handleResize()
</script>

<style>
@import '@/styles/global.scss';
</style>
