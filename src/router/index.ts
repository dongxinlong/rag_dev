import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { getToken } from '@/utils/token'
import { useAuthStore } from '@/stores/auth'

NProgress.configure({ showSpinner: false })

/** 静态路由（不需要权限） */
const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { title: '登录', hidden: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { title: '注册', hidden: true },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPasswordView.vue'),
    meta: { title: '忘记密码', hidden: true },
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/error/NotFound.vue'),
    meta: { title: '404', hidden: true },
  },
]

/** 动态路由（需要权限） */
export const asyncRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
    meta: { hidden: true },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { title: '仪表盘', icon: 'Odometer' },
    children: [
      {
        path: '',
        name: 'DashboardIndex',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '仪表盘' },
      },
    ],
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/chat',
    meta: { title: 'AI 对话', icon: 'ChatDotRound' },
    children: [
      {
        path: '',
        name: 'ChatIndex',
        component: () => import('@/views/chat/ChatView.vue'),
        meta: { title: '对话', affix: true },
      },
    ],
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/knowledge/list',
    meta: { title: '知识库管理', icon: 'Collection' },
    children: [
      {
        path: 'list',
        name: 'KnowledgeList',
        component: () => import('@/views/knowledge/KnowledgeList.vue'),
        meta: { title: '知识库列表' },
      },
      {
        path: 'detail',
        name: 'KnowledgeDetail',
        component: () => import('@/views/knowledge/KnowledgeDetail.vue'),
        meta: { title: '知识库详情', hidden: true },
      },
      {
        path: 'recycle-bin',
        name: 'RecycleBin',
        component: () => import('@/views/knowledge/RecycleBin.vue'),
        meta: { title: '回收站' },
      },
    ],
  },
  {
    path: '/system',
    name: 'System',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/system/user',
    meta: { title: '系统管理', icon: 'Setting' },
    children: [
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/system/ProfileView.vue'),
        meta: { title: '个人中心' },
      },
      {
        path: 'user',
        name: 'SysUser',
        component: () => import('@/views/system/UserManage.vue'),
        meta: { title: '用户管理', permission: 'sys:user:list' },
      },
      {
        path: 'role',
        name: 'SysRole',
        component: () => import('@/views/system/RoleManage.vue'),
        meta: { title: '角色管理', permission: 'sys:role:list' },
      },
      {
        path: 'menu',
        name: 'SysMenu',
        component: () => import('@/views/system/MenuManage.vue'),
        meta: { title: '菜单管理', permission: 'sys:menu:list' },
      },
      {
        path: 'dept',
        name: 'SysDept',
        component: () => import('@/views/system/DeptManage.vue'),
        meta: { title: '部门管理', permission: 'sys:dept:list' },
      },
      {
        path: 'post',
        name: 'SysPost',
        component: () => import('@/views/system/PostManage.vue'),
        meta: { title: '岗位管理', permission: 'sys:post:list' },
      },
      {
        path: 'dict',
        name: 'SysDict',
        component: () => import('@/views/system/DictManage.vue'),
        meta: { title: '字典管理', permission: 'sys:dict:list' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [...constantRoutes, ...asyncRoutes],
})

/** 白名单：不需要登录的页面 */
const whiteList = ['/login', '/register', '/forgot-password', '/404']

/** 路由守卫：鉴权 */
router.beforeEach(async (to, _from, next) => {
  NProgress.start()
  document.title = `${to.meta.title || ''} - RAG 知识库`

  const token = getToken()

  if (token) {
    if (to.path === '/login') {
      // 已登录，跳转首页
      next({ path: '/' })
    } else {
      // 有 token 但没有 user 信息（刷新页面后），自动获取
      const authStore = useAuthStore()
      if (!authStore.user) {
        try {
          await authStore.fetchUserInfo()
        } catch {
          // token 失效，fetchUserInfo 内部会调用 logout 跳转登录页
          return
        }
      }
      next()
    }
  } else {
    if (whiteList.includes(to.path)) {
      next()
    } else {
      // 未登录，跳转登录页并记录来源
      next({
        path: '/login',
        query: { redirect: to.fullPath },
      })
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
