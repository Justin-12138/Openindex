<script setup lang="ts">
import { computed } from 'vue'
import type { Message } from '@/types'
import { useChatStore, useUIStore } from '@/stores'
import { useMarkdown } from '@/composables/useMarkdown'

const props = defineProps<{
  message: Message
}>()

const chatStore = useChatStore()
const uiStore = useUIStore()
const { renderContent } = useMarkdown()

const isUser = computed(() => props.message.role === 'user')

// 点击引用
function handleReferenceClick(ref: any) {
  if (ref.page_num && ref.bbox) {
    uiStore.highlightPdf(ref.page_num, ref.bbox)
  }
  
  // 更新引用面板
  if (props.message.references) {
    chatStore.setActiveReference(props.message.references)
  }
}

// 格式化时间
function formatTime(dateStr?: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="message" :class="{ 'message-user': isUser, 'message-assistant': !isUser }">
    <div class="message-avatar">
      {{ isUser ? '👤' : '🤖' }}
    </div>
    
    <div class="message-content">
      <div class="message-header">
        <span class="message-role">{{ isUser ? '你' : 'AI' }}</span>
        <span class="message-time">{{ formatTime(message.created_at) }}</span>
      </div>
      
      <div class="message-text" v-html="renderContent(message.content)"></div>
      
      <!-- 引用来源 -->
      <div v-if="message.references?.length" class="message-refs">
        <div class="refs-label">📎 引用来源</div>
        <div class="refs-list">
          <button
            v-for="(ref, idx) in message.references.slice(0, 5)"
            :key="idx"
            class="ref-chip"
            @click="handleReferenceClick(ref)"
          >
            <span v-if="ref.page_num" class="ref-page">P{{ ref.page_num }}</span>
            <span class="ref-title truncate">{{ ref.title || ref.context?.slice(0, 30) || '引用' }}</span>
          </button>
          <span v-if="message.references.length > 5" class="refs-more">
            +{{ message.references.length - 5 }} 更多
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.message {
  display: flex;
  gap: 12px;
  animation: slideUp 0.2s ease;
  
  &.message-user {
    flex-direction: row-reverse;
    
    .message-content {
      align-items: flex-end;
    }
    
    .message-text {
      background: var(--primary);
      color: white;
    }
    
    .message-header {
      flex-direction: row-reverse;
    }
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: 50%;
  font-size: 18px;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 80%;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.message-role {
  font-weight: 500;
  color: var(--text-primary);
}

.message-time {
  color: var(--text-muted);
}

.message-text {
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: 16px;
  line-height: 1.6;
  word-break: break-word;

  // Markdown 样式
  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    margin: 8px 0 4px 0;
    font-weight: 600;
    line-height: 1.3;
    color: var(--text-primary);
  }

  :deep(h1) { font-size: 1.4em; }
  :deep(h2) { font-size: 1.3em; }
  :deep(h3) { font-size: 1.2em; }
  :deep(h4) { font-size: 1.1em; }
  :deep(h5) { font-size: 1.05em; }
  :deep(h6) { font-size: 1em; }

  :deep(p) {
    margin: 4px 0;
  }

  :deep(strong), :deep(b) {
    font-weight: 600;
    color: var(--text-primary);
  }

  :deep(em), :deep(i) {
    font-style: italic;
  }

  :deep(code) {
    background: var(--bg-secondary);
    padding: 2px 4px;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
  }

  :deep(pre) {
    background: var(--bg-secondary);
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      background: transparent;
      padding: 0;
      font-size: 0.9em;
      line-height: 1.4;
    }
  }

  :deep(blockquote) {
    border-left: 3px solid var(--primary);
    padding-left: 12px;
    margin: 8px 0;
    color: var(--text-secondary);
    font-style: italic;
  }

  :deep(ul), :deep(ol) {
    margin: 8px 0;
    padding-left: 20px;
  }

  :deep(li) {
    margin: 2px 0;
  }

  :deep(a) {
    color: var(--primary);
    text-decoration: underline;

    &:hover {
      opacity: 0.8;
    }
  }

  // KaTeX 数学公式样式
  :deep(.katex) {
    font-size: 1.1em;
  }

  :deep(.katex-display) {
    margin: 12px 0;
    text-align: center;
  }
}

.message-refs {
  margin-top: 8px;
}

.refs-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.refs-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--bg-tertiary);
  border-radius: 14px;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all 0.15s ease;
  max-width: 200px;
  
  &:hover {
    background: var(--bg-elevated);
    color: var(--primary);
  }
}

.ref-page {
  background: var(--primary);
  color: white;
  padding: 1px 5px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 500;
}

.ref-title {
  flex: 1;
  min-width: 0;
}

.refs-more {
  font-size: 11px;
  color: var(--text-muted);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
