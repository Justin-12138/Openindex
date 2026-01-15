<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useDocumentStore, useChatStore, useUIStore } from '@/stores'
import IconSend from '../icons/IconSend.vue'
import IconPlus from '../icons/IconPlus.vue'
import MessageBubble from './MessageBubble.vue'
import LoadingSpinner from '../common/LoadingSpinner.vue'

const docStore = useDocumentStore()
const chatStore = useChatStore()
const uiStore = useUIStore()

const inputRef = ref<HTMLTextAreaElement | null>(null)
const messagesRef = ref<HTMLDivElement | null>(null)
const query = ref('')

// 发送查询
async function sendQuery() {
  const q = query.value.trim()
  if (!q || !docStore.currentDoc || chatStore.querying) return
  
  query.value = ''
  
  try {
    await chatStore.sendQuery(docStore.currentDoc.id, q)
    scrollToBottom()
  } catch (err: any) {
    uiStore.showToast(err.message || '查询失败', 'error')
  }
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// 新建对话
async function newConversation() {
  if (!docStore.currentDoc) return
  
  try {
    await chatStore.createConversation(docStore.currentDoc.id)
    uiStore.showToast('已创建新对话', 'success')
  } catch (err: any) {
    uiStore.showToast(err.message || '创建失败', 'error')
  }
}

// 处理输入框
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendQuery()
  }
}

function autoResize() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 150) + 'px'
  }
}

// 监听消息变化，自动滚动
watch(() => chatStore.messages.length, () => {
  scrollToBottom()
})

// 文档状态提示
const statusMessage = computed(() => {
  if (!docStore.currentDoc) return null
  
  switch (docStore.currentDoc.status) {
    case 'pending':
      return { type: 'warning', text: '文档待解析，请先解析后再提问' }
    case 'parsing':
      return { type: 'info', text: '文档正在解析中，请稍候...' }
    case 'error':
      return { type: 'error', text: `解析失败: ${docStore.currentDoc.error_message || '未知错误'}` }
    default:
      return null
  }
})
</script>

<template>
  <div class="chat-panel">
    <!-- 头部 -->
    <div class="chat-header">
      <div class="header-left">
        <h2 class="chat-title">
          {{ chatStore.currentConversation?.title || '新对话' }}
        </h2>
        <span v-if="chatStore.conversations.length > 1" class="conv-count">
          {{ chatStore.conversations.length }} 个对话
        </span>
      </div>
      <button class="icon-btn" @click="newConversation" title="新建对话">
        <IconPlus />
      </button>
    </div>

    <!-- 状态提示 -->
    <div v-if="statusMessage" class="status-banner" :class="`status-${statusMessage.type}`">
      {{ statusMessage.text }}
      <button 
        v-if="statusMessage.type === 'warning'" 
        class="btn btn-sm btn-primary"
        @click="docStore.parseDocument"
        :disabled="docStore.parsing"
      >
        {{ docStore.parsing ? '解析中...' : '开始解析' }}
      </button>
    </div>

    <!-- 消息列表 -->
    <div ref="messagesRef" class="messages-container">
      <div v-if="chatStore.messages.length === 0" class="welcome-message">
        <div class="welcome-icon">💬</div>
        <h3>开始对话</h3>
        <p>输入问题，AI 将基于文档内容为您解答</p>
        <div class="example-queries">
          <button class="example-btn" @click="query = '这篇文档的主要内容是什么？'">
            这篇文档的主要内容是什么？
          </button>
          <button class="example-btn" @click="query = '总结一下关键要点'">
            总结一下关键要点
          </button>
        </div>
      </div>
      
      <template v-else>
        <MessageBubble
          v-for="msg in chatStore.messages"
          :key="msg.id"
          :message="msg"
        />
        
        <div v-if="chatStore.querying" class="thinking-indicator">
          <LoadingSpinner size="sm" />
          <span>思考中...</span>
        </div>
      </template>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
      <div class="input-wrapper">
        <textarea
          ref="inputRef"
          v-model="query"
          placeholder="输入问题..."
          rows="1"
          @keydown="handleKeyDown"
          @input="autoResize"
          :disabled="chatStore.querying || !docStore.isReady"
        />
        <button 
          class="send-btn"
          @click="sendQuery"
          :disabled="!query.trim() || chatStore.querying || !docStore.isReady"
        >
          <IconSend />
        </button>
      </div>
      <div class="input-hint">
        <span class="shortcut">Enter</span> 发送 · 
        <span class="shortcut">Shift + Enter</span> 换行
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-title {
  font-size: 16px;
  font-weight: 600;
}

.conv-count {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 10px;
}

.status-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 10px 16px;
  font-size: 13px;
  flex-shrink: 0;
  
  &.status-warning {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning);
  }
  
  &.status-info {
    background: rgba(59, 130, 246, 0.1);
    color: var(--info);
  }
  
  &.status-error {
    background: rgba(239, 68, 68, 0.1);
    color: var(--error);
  }
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
  margin: auto;
  
  .welcome-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
  }
  
  p {
    color: var(--text-secondary);
    margin-bottom: 24px;
  }
}

.example-queries {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.example-btn {
  padding: 8px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: 20px;
  transition: all 0.15s ease;
  
  &:hover {
    background: var(--bg-elevated);
    color: var(--primary);
  }
}

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color 0.15s ease;
  
  &:focus-within {
    border-color: var(--primary);
  }
  
  textarea {
    flex: 1;
    border: none;
    background: transparent;
    resize: none;
    min-height: 24px;
    max-height: 150px;
    line-height: 1.5;
    
    &:focus {
      outline: none;
      box-shadow: none;
    }
    
    &:disabled {
      opacity: 0.6;
    }
  }
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--primary);
  color: white;
  border-radius: 8px;
  transition: all 0.15s ease;
  flex-shrink: 0;
  
  &:hover:not(:disabled) {
    background: var(--primary-hover);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  svg {
    width: 18px;
    height: 18px;
  }
}

.input-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.shortcut {
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-family: monospace;
}
</style>
