import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi } from '@/api/auth'
import { getUserInfo } from '@/api/system'
import { setToken, getToken, clearTokens } from '@/utils/token'
import router from '@/router'
import type { UserResponse } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  /** 初始化时从 localStorage 恢复 token */
  const token = ref<string | null>(getToken())
  const user = ref<UserResponse | null>(null)

  /** 登录 — TokenResponse 包含 access_token + user */
  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    const { access_token, user: userInfo } = res.data
    setToken(access_token)
    token.value = access_token
    user.value = userInfo
  }

  /** 刷新用户信息（页面刷新后从后端重新获取） */
  async function fetchUserInfo() {
    if (!token.value) return
    try {
      const res = await getUserInfo()
      user.value = res.data
    } catch {
      // token 无效，清除
      logout()
    }
  }

  /** 登出 */
  function logout() {
    clearTokens()
    token.value = null
    user.value = null
    router.push('/login')
  }

  function isAuthenticated(): boolean {
    return !!getToken()
  }

  function setUserInfo(info: UserResponse) {
    user.value = info
  }

  function hasPermission(perm: string): boolean {
    if (user.value?.is_admin) return true
    return false
  }

  return {
    token,
    user,
    login,
    logout,
    isAuthenticated,
    fetchUserInfo,
    setUserInfo,
    hasPermission,
  }
})
