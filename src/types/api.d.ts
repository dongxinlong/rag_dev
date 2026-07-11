/** ═══ 通用响应 ═══ */
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PageResponse<T = any> {
  code: number
  message: string
  page: number
  size: number
  total: number
  items: T[]
}

export interface PageParams {
  page?: number
  size?: number
}

/** ═══ 用户模块 ═══ */
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  nickname?: string
}

export interface UserResponse {
  id: number
  username: string
  email: string
  nickname?: string
  avatar?: string
  is_active: boolean
  is_admin: boolean
  created_at?: string
}

export interface UserUpdate {
  nickname?: string
  avatar?: string
  email?: string
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** ═══ 知识库模块 ═══ */
export interface CategoryCreate {
  name: string
  description?: string
  parent_id?: number
  sort_order?: number
  icon?: string
}

export interface CategoryUpdate {
  name?: string
  description?: string
  parent_id?: number
  sort_order?: number
  icon?: string
}

export interface CategoryResponse {
  id: number
  name: string
  description?: string
  icon?: string
  parent_id: number
  sort_order: number
  creator_id?: string
  creator_name?: string
  created_at?: string
}

export interface KnowledgeBaseResponse {
  id: string
  name: string
  file_ext?: string
  file_size?: number
  minio_key?: string
  parsed_minio_key?: string
  status?: string
  creator_id?: string
  creator_name?: string
  is_folder: boolean
  parent_id: number
  path: string
  level: number
  sort_order: number
  title?: string
  created_at?: string
  updated_at?: string
}

export interface KnowledgeBaseUpdate {
  name?: string
  category_id?: number
  parent_id?: number
  sort_order?: number
}

/** ═══ 对话模块 ═══ */
export interface ChatCreate {
  title?: string
}

export interface ChatResponse {
  id: string
  title: string
  created_at: string
  updated_at: string
}

/** ═══ 消息模块 ═══ */
export interface MessageResponse {
  id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  tokens_prompt?: number
  tokens_completion?: number
  cache_tokens?: number
  model?: string
  cost?: number
  extra_data?: {
    sources?: Source[]
  } | null
  status: 'generating' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

/** ═══ RAG 模块 ═══ */
export interface RAGQueryResponse {
  answer: string
  sources: Source[]
  cost: number
}

export interface Source {
  content: string
  similarity: number
  file_name: string
}
