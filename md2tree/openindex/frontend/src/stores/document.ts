import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { Document, TreeNode } from '@/types'
import { api } from '@/composables/useApi'
import { useChatStore } from './chat'

const CURRENT_DOC_KEY = 'openindex_current_doc_id'

export const useDocumentStore = defineStore('document', () => {
  // 状态
  const currentDoc = ref<Document | null>(null)
  const treeData = ref<TreeNode[] | null>(null)
  const treeStats = ref<Record<string, number> | null>(null)
  const loading = ref(false)
  const parsing = ref(false)

  // 计算属性
  const pdfUrl = computed(() => 
    currentDoc.value?.id ? api.documents.getPdfUrl(currentDoc.value.id) : null
  )

  const isReady = computed(() => currentDoc.value?.status === 'ready')
  const isParsing = computed(() => currentDoc.value?.status === 'parsing')
  const hasError = computed(() => currentDoc.value?.status === 'error')

  // 方法
  async function selectDocument(doc: Document) {
    // 切换文档时，清空之前文档的聊天状态
    const chatStore = useChatStore()
    chatStore.clearForDocument()
    
    currentDoc.value = doc
    treeData.value = null
    treeStats.value = null
    
    // 保存当前文档 ID 到 localStorage
    if (doc) {
      localStorage.setItem(CURRENT_DOC_KEY, doc.id)
    } else {
      localStorage.removeItem(CURRENT_DOC_KEY)
    }

    if (doc.status === 'ready') {
      await loadTree()
      // 加载新文档的对话列表（切换文档时不恢复对话，总是加载最新的）
      await chatStore.loadConversations(doc.id, null)
    }
  }
  
  // 恢复文档状态（页面刷新后调用）
  async function restoreDocument() {
    const savedDocId = localStorage.getItem(CURRENT_DOC_KEY)
    if (!savedDocId) return
    
    try {
      loading.value = true
      const doc = await api.documents.get(savedDocId)
      if (doc) {
        // 直接设置文档，不调用 selectDocument 避免重复清空
        const chatStore = useChatStore()
        currentDoc.value = doc
        treeData.value = null
        treeStats.value = null
        
        if (doc.status === 'ready') {
          await loadTree()
          // 尝试恢复保存的对话 ID
          const savedConvId = localStorage.getItem('openindex_current_conv_id')
          // 加载新文档的对话列表，并尝试恢复对话
          await chatStore.loadConversations(doc.id, savedConvId)
        }
      } else {
        // 文档不存在，清除保存的 ID
        localStorage.removeItem(CURRENT_DOC_KEY)
        localStorage.removeItem('openindex_current_conv_id')
      }
    } catch (e) {
      console.error('Failed to restore document:', e)
      // 恢复失败，清除保存的 ID
      localStorage.removeItem(CURRENT_DOC_KEY)
      localStorage.removeItem('openindex_current_conv_id')
    } finally {
      loading.value = false
    }
  }

  async function loadTree() {
    if (!currentDoc.value) return
    
    try {
      loading.value = true
      const result = await api.documents.getTree(currentDoc.value.id)
      treeData.value = result.structure
      treeStats.value = result.stats
    } catch (e) {
      console.error('Failed to load tree:', e)
    } finally {
      loading.value = false
    }
  }

  async function parseDocument() {
    if (!currentDoc.value) return
    
    try {
      parsing.value = true
      currentDoc.value.status = 'parsing'
      await api.documents.parse(currentDoc.value.id)
      
      // 开始轮询状态
      pollStatus()
    } catch (e: any) {
      currentDoc.value.status = 'error'
      currentDoc.value.error_message = e.message
      parsing.value = false
      throw e
    }
  }

  async function pollStatus() {
    if (!currentDoc.value) return

    const poll = async () => {
      if (!currentDoc.value) return
      
      try {
        const doc = await api.documents.get(currentDoc.value.id)
        currentDoc.value = doc

        if (doc.status === 'parsing') {
          setTimeout(poll, 2000)
        } else if (doc.status === 'ready') {
          parsing.value = false
          await loadTree()
        } else {
          parsing.value = false
        }
      } catch (e) {
        console.error('Poll status failed:', e)
        parsing.value = false
      }
    }

    poll()
  }

  function clearDocument() {
    currentDoc.value = null
    treeData.value = null
    treeStats.value = null
    // 清除保存的文档 ID
    localStorage.removeItem(CURRENT_DOC_KEY)
  }

  return {
    // 状态
    currentDoc,
    treeData,
    treeStats,
    loading,
    parsing,
    // 计算属性
    pdfUrl,
    isReady,
    isParsing,
    hasError,
    // 方法
    selectDocument,
    loadTree,
    parseDocument,
    clearDocument,
    restoreDocument
  }
})
