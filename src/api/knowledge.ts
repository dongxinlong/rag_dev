import { get, post, put, del, upload } from './request'
import service from './request'
import type {
  CategoryCreate, CategoryUpdate, CategoryResponse,
  KnowledgeBaseResponse, KnowledgeBaseUpdate, PageParams,
} from '@/types/api'

/** ═══ 分类管理 ═══ */
export function listCategories(params?: PageParams & { keyword?: string }) {
  return get<CategoryResponse[]>('/v1/knowledge/category/list', params)
}

export function createCategory(data: CategoryCreate) {
  return post<CategoryResponse>('/v1/knowledge/category', data)
}

export function updateCategory(id: number, data: CategoryUpdate) {
  return put<CategoryResponse>(`/v1/knowledge/category/${id}`, data)
}

export function deleteCategory(id: number) {
  return del(`/v1/knowledge/category/${id}`)
}

/** ═══ 知识库/文件管理 ═══ */
export function listKnowledgeBases(params?: PageParams & { parent_id?: string; category_id?: string }) {
  return get<KnowledgeBaseResponse[]>('/v1/knowledge/list', params)
}

export function getKnowledgeBase(id: string) {
  return get<KnowledgeBaseResponse>(`/v1/knowledge/${id}`)
}

export function createFolder(name: string, category_id: string, parent_id?: string) {
  const params: Record<string, string> = { name, category_id }
  if (parent_id) params.parent_id = parent_id
  return post<KnowledgeBaseResponse>('/v1/knowledge/folder', null, { params })
}

export function updateKnowledgeBase(id: string, data: KnowledgeBaseUpdate) {
  return put<KnowledgeBaseResponse>(`/v1/knowledge/${id}`, data)
}

export function deleteKnowledgeBase(id: string) {
  return del(`/v1/knowledge/${id}`)
}

export function moveKnowledgeBase(id: string, target_parent_id: string) {
  return post<KnowledgeBaseResponse>(`/v1/knowledge/${id}/move`, null, {
    params: { target_parent_id },
  })
}

export function getKnowledgeTree(parent_id?: string) {
  const params: Record<string, string> = {}
  if (parent_id) params.parent_id = parent_id
  return get('/v1/knowledge/tree', params)
}

/** ═══ 文件搜索 ═══ */
export interface SearchResult {
  id: string
  name: string
  path: string
  file_ext?: string
  file_size?: number
  is_folder: boolean
  status?: string
  created_at?: string
}

export function searchFiles(params: { keyword: string; parent_id?: string; category_id?: string }) {
  return get<SearchResult[]>('/v1/knowledge/search', params)
}

/** ═══ 文件夹树 ═══ */
export interface FolderTreeNode {
  id: string
  name: string
  path: string
  children?: FolderTreeNode[]
}

export function getFolderTree(categoryId: string, parentId?: string) {
  const params: Record<string, string> = { category_id: categoryId }
  if (parentId) params.parent_id = parentId
  return get<FolderTreeNode[]>('/v1/knowledge/folder-tree', params)
}

/** ═══ 重命名 ═══ */
export function renameFile(kbId: string, newName: string) {
  return post<KnowledgeBaseResponse>('/v1/knowledge/rename', null, {
    params: { kb_id: kbId, new_name: newName },
  })
}

/** ═══ 移动/复制 ═══ */
export function moveFile(kbId: string, targetParentId: string) {
  return post<KnowledgeBaseResponse>('/v1/knowledge/move', null, {
    params: { kb_id: kbId, target_parent_id: targetParentId },
  })
}

export function copyFile(kbId: string, targetParentId: string) {
  return post<KnowledgeBaseResponse>('/v1/knowledge/copy', null, {
    params: { kb_id: kbId, target_parent_id: targetParentId },
  })
}

/** ═══ 文件预览 ═══ */
export interface PreviewResponse {
  url: string
  name: string
  ext: string
}

export function getPreviewUrl(kbId: string) {
  return get<PreviewResponse>(`/v1/knowledge/preview/${kbId}`)
}

/** ═══ 面包屑导航 ═══ */
export interface NavigationItem {
  id: string
  name: string
  path: string
}

export function getNavigation(kbId: string) {
  return get<NavigationItem[]>(`/v1/knowledge/navigation/${kbId}`)
}

/** ═══ 文件上传 ═══ */
export function uploadFile(file: File, category_id: string, parent_id?: string, onProgress?: (p: number) => void) {
  const formData = new FormData()
  formData.append('file', file)

  const params: Record<string, string> = { category_id }
  if (parent_id) params.parent_id = parent_id

  return service.post('/v1/knowledge/upload', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  }).then((res: any) => res.data)
}

/** ═══ 回收站 ═══ */
export interface RecycleBinParams {
  page: number
  size: number
  keyword?: string
}

export interface RecycleBinListResult {
  code: number
  message: string
  items: KnowledgeBaseResponse[]
  total: number
  page: number
  size: number
}

export function getRecycleBinList(params: RecycleBinParams) {
  return get('/v1/knowledge/recycle-bin', params) as Promise<RecycleBinListResult>
}

export function restoreFromRecycleBin(kbId: string) {
  return post(`/v1/knowledge/recycle-bin/${kbId}/restore`)
}

export function permanentDelete(kbId: string) {
  return del(`/v1/knowledge/recycle-bin/${kbId}`)
}

export function clearRecycleBin() {
  return del('/v1/knowledge/recycle-bin/clear')
}
