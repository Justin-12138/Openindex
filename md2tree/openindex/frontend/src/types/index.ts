// 文档库
export interface Library {
  id: string
  name: string
  description?: string
  color: string
  icon: string
  document_count: number
  created_at: string
  updated_at: string
}

// 文档
export interface Document {
  id: string
  name: string
  original_filename?: string
  pdf_path?: string
  library_id?: string | null
  status: 'pending' | 'parsing' | 'ready' | 'error'
  stats?: {
    total_nodes: number
    max_depth: number
    total_pages: number
  }
  file_size?: number
  created_at?: string
  error_message?: string
}

// 对话
export interface Conversation {
  id: string
  doc_id: string
  title: string
  created_at: string
  updated_at: string
  message_count?: number
  messages?: Message[]
}

// 消息
export interface Message {
  id: number
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  references?: Reference[]
  selected_nodes?: SelectedNode[]
  locations?: NodeLocation[]
  created_at?: string
}

// 引用
export interface Reference {
  type: 'node' | 'block'
  node_id?: string
  title?: string
  page_num?: number
  bbox?: number[]
  block_type?: string
  context?: string
  reason?: string
}

// 选中的节点
export interface SelectedNode {
  node_id: string
  title: string
  relevance?: number
  reason?: string
}

// 节点位置
export interface NodeLocation {
  node_id: string
  title: string
  page_range?: number[]
  title_block?: BlockLocation
  content_blocks?: BlockLocation[]
}

// 块位置
export interface BlockLocation {
  page_idx: number
  page_num: number
  bbox: number[]
  type: string
}

// 树节点
export interface TreeNode {
  title: string
  node_id?: string
  text?: string
  summary?: string
  level?: number
  nodes?: TreeNode[]
  page_info?: {
    page_range?: number[]
    title_block?: BlockLocation
    content_blocks?: BlockLocation[]
  }
}

// 查询响应
export interface QueryResponse {
  query: string
  answer: string
  selected_nodes: SelectedNode[]
  locations: NodeLocation[]
  sources: Reference[]
}

// Toast 类型
export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading'

export interface Toast {
  id: number
  type: ToastType
  message: string
  duration?: number
}
