<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside
      :width="appStore.sidebarCollapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)'"
      class="layout-aside"
    >
      <div class="sidebar-logo" @click="$router.push('/')">
        <img src="@/assets/logo.svg" alt="Logo" class="logo-img" v-if="!appStore.sidebarCollapsed" />
        <span class="logo-text" v-if="!appStore.sidebarCollapsed">RAG 知识库</span>
        <span class="logo-text" v-else>R</span>
      </div>

      <el-scrollbar class="sidebar-menu-wrap">
        <el-menu
          :default-active="activeMenu"
          :collapse="appStore.sidebarCollapsed"
          :collapse-transition="false"
          router
          background-color="var(--sidebar-bg)"
          text-color="var(--sidebar-text)"
          active-text-color="var(--sidebar-text-active)"
        >
          <template v-for="route in menuRoutes" :key="route.path">
            <!-- 单级菜单 -->
            <el-menu-item
              v-if="visibleChildren(route).length <= 1"
              :index="getMenuPath(route)"
            >
              <el-icon v-if="route.meta?.icon">
                <component :is="route.meta.icon" />
              </el-icon>
              <template #title>{{ route.meta?.title }}</template>
            </el-menu-item>

            <!-- 多级菜单 -->
            <el-sub-menu v-else :index="route.path">
              <template #title>
                <el-icon v-if="route.meta?.icon">
                  <component :is="route.meta.icon" />
                </el-icon>
                <span>{{ route.meta?.title }}</span>
              </template>

              <el-menu-item
                v-for="child in visibleChildren(route)"
                :key="child.path"
                :index="`${route.path}/${child.path}`"
              >
                {{ child.meta?.title }}
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="layout-main">
      <!-- 顶栏 -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon
            class="collapse-btn"
            @click="appStore.toggleSidebar"
          >
            <component :is="appStore.sidebarCollapsed ? 'Expand' : 'Fold'" />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item
              v-for="item in breadcrumbs"
              :key="item.path"
              :to="item.path !== currentPath ? { path: item.path } : undefined"
            >
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 全屏 -->
          <el-tooltip content="全屏" placement="bottom">
            <el-icon class="header-icon" @click="toggleFullscreen">
              <FullScreen />
            </el-icon>
          </el-tooltip>

          <!-- 用户下拉菜单 -->
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-info">
              <el-avatar :size="32" class="user-avatar">
                <img v-if="authStore.user?.avatar" :src="authStore.user.avatar" alt="头像" />
                <span v-else>{{ authStore.user?.nickname?.[0] || 'U' }}</span>
              </el-avatar>
              <span class="user-name">{{ authStore.user?.nickname || '未登录' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人中心
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { asyncRoutes } from '@/router'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

/** 当前激活的菜单路径 */
const activeMenu = computed(() => route.meta?.activeMenu as string || route.path)

/** 可显示的菜单路由 */
const menuRoutes = computed(() => {
  return asyncRoutes.filter(r => !r.meta?.hidden)
})

/** 过滤掉 hidden 的子路由 */
function visibleChildren(route: any) {
  return (route.children || []).filter((c: any) => !c.meta?.hidden)
}

/** 面包屑 */
const breadcrumbs = computed(() => {
  return route.matched
    .filter(r => r.meta?.title)
    .map(r => ({
      path: r.path,
      title: r.meta.title as string,
    }))
})

const currentPath = computed(() => route.path)

function getMenuPath(route: any): string {
  const visible = visibleChildren(route)
  if (visible.length === 1) {
    return `${route.path}/${visible[0].path}`
  }
  return route.redirect || route.path
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

function handleUserCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
  } else if (command === 'profile') {
    router.push('/system/profile')
  }
}
</script>

<style lang="scss" scoped>
.layout {
  height: 100vh;
  overflow: hidden;
}

.layout-aside {
  background: var(--sidebar-bg);
  transition: width var(--duration-normal) var(--ease-out);
  overflow: hidden;
  border-right: 1px solid oklch(0.20 0.015 260);
}

.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 16px;
  cursor: pointer;
  border-bottom: 1px solid oklch(0.20 0.015 260);
  overflow: hidden;

  .logo-img {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
  }

  .logo-text {
    font-size: var(--text-md);
    font-weight: 700;
    color: var(--sidebar-text-active);
    white-space: nowrap;
    letter-spacing: -0.01em;
  }
}

.sidebar-menu-wrap {
  height: calc(100vh - 56px);
}

// 菜单样式覆盖
:deep(.el-menu) {
  border-right: none !important;

  .el-menu-item,
  .el-sub-menu__title {
    height: 44px;
    line-height: 44px;
    margin: 2px 8px;
    border-radius: var(--radius-md);
    transition: all var(--duration-fast) var(--ease-out);

    &:hover {
      background: var(--sidebar-bg-hover) !important;
    }
  }

  .el-menu-item.is-active {
    background: var(--sidebar-bg-active) !important;
    color: var(--sidebar-text-active) !important;
    font-weight: 500;
  }
}

.layout-main {
  flex-direction: column;
  overflow: hidden;
}

.layout-header {
  height: 56px;
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: var(--z-sticky);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;

  .collapse-btn {
    font-size: 20px;
    cursor: pointer;
    color: var(--color-text-secondary);
    transition: color var(--duration-fast);

    &:hover {
      color: var(--color-primary);
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  font-size: 18px;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: color var(--duration-fast);

  &:hover {
    color: var(--color-primary);
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-md);
  transition: background var(--duration-fast);

  &:hover {
    background: var(--color-bg-hover);
  }

  .user-avatar {
    background: var(--color-primary);
    color: white;
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .user-name {
    font-size: var(--text-sm);
    color: var(--color-text-regular);
  }
}

.layout-content {
  background: var(--color-bg-page);
  overflow-y: auto;
  padding: 0;
  flex: 1;
  min-height: 0;
}

// 路由过渡动画
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all var(--duration-normal) var(--ease-out);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
