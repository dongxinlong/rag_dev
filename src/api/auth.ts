import { post } from './request'
import type { LoginRequest, TokenResponse, RegisterRequest, UserResponse, ChangePasswordRequest } from '@/types/api'

/** 用户登录 */
export function login(data: LoginRequest) {
  return post<TokenResponse>('/v1/user/login', data)
}

/** 用户注册 */
export function register(data: RegisterRequest) {
  return post<UserResponse>('/v1/user/register', data)
}

/** 修改密码 */
export function changePassword(data: ChangePasswordRequest) {
  return post('/v1/user/change-password', data)
}
