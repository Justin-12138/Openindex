import type { Library, Document, Conversation, Message, QueryResponse, TreeNode } from '@/types'

const BASE_URL = 'http://localhost:8090'

class ApiError extends Error {
  status: number
  
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  })
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, error.detail || error.message || 'Request failed')
  }
  
  return res.json()
}

export const api = {
  // 库管理
  libraries: {
    list: () => request<Library[]>('/api/libraries'),
    
    get: (id: string) => request<Library>(`/api/libraries/${id}`),
    
    create: (data: { name: string; description?: string; color?: string; icon?: string }) =>
      request<Library>('/api/libraries', {
        method: 'POST',
        body: JSON.stringify(data)
      }),
    
    update: (id: string, data: Partial<Library>) =>
      request<Library>(`/api/libraries/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
      }),
    
    delete: (id: string) =>
      request<{ message: string }>(`/api/libraries/${id}`, { method: 'DELETE' }),
    
    getDocuments: (id: string) =>
      request<Document[]>(`/api/libraries/${id}/documents`)
  },

  // 文档管理
  documents: {
    list: () => request<Document[]>('/api/documents'),
    
    get: (id: string) => request<Document>(`/api/documents/${id}`),
    
    upload: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      
      const res = await fetch(`${BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData
      })
      
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }))
        throw new ApiError(res.status, error.detail || 'Upload failed')
      }
      
      return res.json()
    },
    
    delete: (id: string) =>
      request<{ message: string }>(`/api/documents/${id}`, { method: 'DELETE' }),
    
    move: (id: string, libraryId: string | null) =>
      request<{ message: string }>(`/api/documents/${id}/move`, {
        method: 'POST',
        body: JSON.stringify({ library_id: libraryId })
      }),
    
    parse: (id: string) =>
      request<{ message: string; status: string }>(`/api/documents/${id}/parse`, {
        method: 'POST'
      }),
    
    getTree: (id: string) =>
      request<{ doc_id: string; doc_name: string; structure: TreeNode[]; stats: Record<string, number> }>(
        `/api/documents/${id}/tree`
      ),
    
    getPdfUrl: (id: string) => `${BASE_URL}/api/documents/${id}/pdf`,
    
    getUncategorized: () => request<Document[]>('/api/documents/uncategorized')
  },

  // 对话管理
  conversations: {
    list: (docId: string) =>
      request<Conversation[]>(`/api/documents/${docId}/conversations`),
    
    get: (id: string) => request<Conversation>(`/api/conversations/${id}`),
    
    create: (docId: string, title?: string) =>
      request<Conversation>('/api/conversations', {
        method: 'POST',
        body: JSON.stringify({ doc_id: docId, title })
      }),
    
    delete: (id: string) =>
      request<{ message: string }>(`/api/conversations/${id}`, { method: 'DELETE' })
  },

  // 消息
  messages: {
    add: (conversationId: string, role: string, content: string, extras?: {
      references?: any[]
      selected_nodes?: any[]
      locations?: any[]
    }) =>
      request<Message>('/api/messages', {
        method: 'POST',
        body: JSON.stringify({
          conversation_id: conversationId,
          role,
          content,
          ...extras
        })
      })
  },

  // 查询
  query: (docId: string, query: string, conversationId?: string) =>
    request<QueryResponse>('/api/query', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId,
        query,
        conversation_id: conversationId
      })
    }),

  // 统计
  stats: () =>
    request<{
      total_documents: number
      ready_documents: number
      total_conversations: number
      total_messages: number
    }>('/api/stats'),

  // 健康检查
  health: () => request<{ status: string; version: string }>('/health')
}

export function useApi() {
  return api
}
