import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, clearTokens } from '@/utils/token'
import router from '@/router'
import type { ApiResponse } from '@/types/api'

/** 创建 axios 实例 — baseURL=/api，后端路由前缀 /api/v1/... */
const service: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

/** 请求拦截器：自动携带 JWT Token */
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

/** 响应拦截器：统一错误处理 */
service.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const res = response.data

    // 业务逻辑错误
    if (res.code !== 200 && res.code !== 0) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }

    return response
  },
  (error) => {
    // 401: Token 过期或无效
    if (error.response?.status === 401) {
      clearTokens()
      ElMessage.warning('登录已过期，请重新登录')
      router.push({
        path: '/login',
        query: { redirect: router.currentRoute.value.fullPath },
      })
    } else {
      const message = error.response?.data?.message || error.message || '网络错误'
      ElMessage.error(message)
    }

    return Promise.reject(error)
  },
)

/** 封装 GET 请求 */
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return service.get(url, { params, ...config }).then((res) => res.data)
}

/** 封装 POST 请求 */
export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return service.post(url, data, config).then((res) => res.data)
}

/** 封装 PUT 请求 */
export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return service.put(url, data, config).then((res) => res.data)
}

/** 封装 DELETE 请求 */
export function del<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return service.delete(url, { params, ...config }).then((res) => res.data)
}

/** 文件上传 */
export function upload<T = any>(url: string, file: File, onProgress?: (p: number) => void): Promise<ApiResponse<T>> {
  const formData = new FormData()
  formData.append('file', file)

  return service
    .post(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      },
    })
    .then((res) => res.data)
}

export default service
