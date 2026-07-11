import { get, post, put, del } from './request'
import type { ChatCreate, ChatResponse, MessageResponse, RAGQueryResponse, PageParams } from '@/types/api'

/** ═══ 对话管理 ═══ */
export function listChats(params?: PageParams & { keyword?: string }) {
  return get('/v1/chats', params) as Promise<{ items: ChatResponse[]; total: number }>
}

export function createChat(data?: ChatCreate) {
  return post<ChatResponse>('/v1/chats', data || { title: '新对话' })
}

export function deleteChat(chatId: string) {
  return del(`/v1/chats/${chatId}`)
}

export function updateChatTitle(chatId: string, title: string) {
  return put(`/v1/chats/${chatId}`, null, { params: { title } })
}

/** ═══ 消息管理 ═══ */
export interface MessageListResult {
  items: MessageResponse[]
  total: number
  page: number
  size: number
}

export function listMessages(chatId: string, page = 1, size = 50) {
  return get<MessageListResult>('/v1/messages', { chat_id: chatId, page, size })
}

/** ═══ RAG 查询 ═══ */
export function ragQuery(chatId: string, question: string, topK?: number) {
  return get<RAGQueryResponse>('/v1/rag/query', {
    chat_id: chatId,
    question,
    top_k: topK || 5,
  })
}

/** SSE 流式事件 */
export interface StreamEvent {
  type: 'sources' | 'content' | 'cost' | 'error'
  value: any
}

/** 流式查询 — 返回 SSE 事件流 */
export async function* ragQueryStream(
  chatId: string,
  question: string,
  topK?: number,
): AsyncGenerator<StreamEvent> {
  const params = new URLSearchParams({
    chat_id: chatId,
    question,
    top_k: String(topK || 5),
  })

  const response = await fetch(`/api/v1/rag/query/stream?${params}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
    },
  })

  if (!response.ok) throw new Error('流式查询失败')

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // 保留未完成的行

    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = line.slice(5).trim()
        if (data === '[DONE]') return
        if (!data) continue
        try {
          yield JSON.parse(data) as StreamEvent
        } catch {
          // 忽略解析错误
        }
      }
    }
  }
}
