import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, Message, Reference, NodeLocation, SelectedNode } from '@/types'
import { api } from '@/composables/useApi'

const CURRENT_CONV_KEY = 'openindex_current_conv_id'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<Message[]>([])
  const references = ref<Reference[]>([])
  const selectedNodes = ref<SelectedNode[]>([])
  const locations = ref<NodeLocation[]>([])
  const loading = ref(false)
  const querying = ref(false)

  // 计算属性
  const hasMessages = computed(() => messages.value.length > 0)

  // 方法
  async function loadConversations(docId: string, restoreConvId: string | null = null) {
    try {
      loading.value = true
      // 先清空当前状态，确保不会显示其他文档的对话
      clearForDocument()
      
      conversations.value = await api.conversations.list(docId)
      
      // 优先恢复保存的对话，否则加载最近的对话
      let convToLoad: Conversation | null = null
      
      if (restoreConvId) {
        // 尝试恢复保存的对话
        convToLoad = conversations.value.find(c => c.id === restoreConvId) || null
        if (convToLoad) {
          // 保存的对话存在，加载它
          await loadConversation(restoreConvId)
          return
        }
      }
      
      // 没有保存的对话或保存的对话不存在，加载最近的对话
      const firstConv = conversations.value[0]
      if (firstConv) {
        await loadConversation(firstConv.id)
      } else {
        currentConversation.value = null
        messages.value = []
        // 清除保存的对话 ID
        localStorage.removeItem(CURRENT_CONV_KEY)
      }
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      loading.value = false
    }
  }

  async function loadConversation(convId: string) {
    try {
      const conv = await api.conversations.get(convId)
      currentConversation.value = conv
      messages.value = conv.messages || []
      
      // 保存当前对话 ID 到 localStorage
      localStorage.setItem(CURRENT_CONV_KEY, convId)
      
      // 从消息中提取 locations 和 references
      // 只显示当前对话的消息中的标注
      references.value = []
      selectedNodes.value = []
      locations.value = []
      
      // 从最新的 assistant 消息中提取标注信息
      const assistantMessages = messages.value
        .filter(msg => msg.role === 'assistant')
        .reverse() // 从最新到最旧
      
      if (assistantMessages.length > 0) {
        const latestMessage = assistantMessages[0]
        if (latestMessage.references) {
          references.value = latestMessage.references
        }
        if (latestMessage.selected_nodes) {
          selectedNodes.value = latestMessage.selected_nodes
        }
        if (latestMessage.locations) {
          locations.value = latestMessage.locations
        }
      }
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }

  async function createConversation(docId: string) {
    const conv = await api.conversations.create(docId)
    conversations.value.unshift(conv)
    currentConversation.value = conv
    messages.value = []
    // 保存新创建的对话 ID
    localStorage.setItem(CURRENT_CONV_KEY, conv.id)
    return conv
  }

  async function sendQuery(docId: string, query: string) {
    // 确保有对话
    if (!currentConversation.value) {
      await createConversation(docId)
    }

    // 添加用户消息到界面
    const userMessage: Message = {
      id: Date.now(),
      conversation_id: currentConversation.value!.id,
      role: 'user',
      content: query,
      created_at: new Date().toISOString()
    }
    messages.value.push(userMessage)

    try {
      querying.value = true
      
      // 调用查询 API
      const response = await api.query(docId, query, currentConversation.value?.id)
      
      // 更新引用数据
      references.value = response.sources || []
      selectedNodes.value = response.selected_nodes || []
      locations.value = response.locations || []
      
      // 添加 AI 回复
      const assistantMessage: Message = {
        id: Date.now() + 1,
        conversation_id: currentConversation.value!.id,
        role: 'assistant',
        content: response.answer,
        references: response.sources,
        selected_nodes: response.selected_nodes,
        locations: response.locations,
        created_at: new Date().toISOString()
      }
      messages.value.push(assistantMessage)

      return response
    } catch (e: any) {
      // 添加错误消息
      const errorMessage: Message = {
        id: Date.now() + 1,
        conversation_id: currentConversation.value!.id,
        role: 'assistant',
        content: `查询失败: ${e.message}`,
        created_at: new Date().toISOString()
      }
      messages.value.push(errorMessage)
      throw e
    } finally {
      querying.value = false
    }
  }

  function clearChat() {
    conversations.value = []
    currentConversation.value = null
    messages.value = []
    references.value = []
    selectedNodes.value = []
    locations.value = []
    // 清除保存的对话 ID
    localStorage.removeItem(CURRENT_CONV_KEY)
  }

  // 清空当前文档相关的状态（切换文档时调用）
  function clearForDocument() {
    // 只清空与当前文档相关的状态，保留对话列表
    // 但清空消息、引用、位置等，因为这些是特定于当前对话的
    messages.value = []
    references.value = []
    selectedNodes.value = []
    locations.value = []
    // 注意：不清空 conversations 和 currentConversation，因为 loadConversations 会重新加载
    // 但切换文档时，需要清除保存的对话 ID（因为对话属于不同文档）
    localStorage.removeItem(CURRENT_CONV_KEY)
  }

  function setActiveReference(refs: Reference[]) {
    references.value = refs
  }

  return {
    // 状态
    conversations,
    currentConversation,
    messages,
    references,
    selectedNodes,
    locations,
    loading,
    querying,
    // 计算属性
    hasMessages,
    // 方法
    loadConversations,
    loadConversation,
    createConversation,
    sendQuery,
    clearChat,
    clearForDocument,
    setActiveReference
  }
})
