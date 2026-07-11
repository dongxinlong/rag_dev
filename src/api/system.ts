import { get, post, put, del, upload } from './request'
import type { UserResponse, UserUpdate, PageParams } from '@/types/api'

/** ═══ 当前用户 ═══ */
export function getUserInfo() {
  return get<UserResponse>('/v1/user/info')
}

export function updateUserInfo(data: UserUpdate) {
  return put<UserResponse>('/v1/user/info', data)
}

export function uploadAvatar(file: File) {
  return upload('/v1/user/avatar', file)
}

/** ═══ 用户管理（管理员） ═══ */
export function listUsers(params?: PageParams & { keyword?: string }) {
  return get<UserResponse[]>('/v1/user/list', params)
}

export function deleteUser(userId: number) {
  return del(`/v1/user/${userId}`)
}

export function toggleUserActive(userId: number) {
  return post<UserResponse>(`/v1/user/${userId}/toggle-active`)
}
