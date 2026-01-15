<script setup lang="ts">
import { useChatStore, useUIStore } from '@/stores'

const chatStore = useChatStore()
const uiStore = useUIStore()

function handleBlockClick(ref: any) {
  if (ref.page_num && ref.bbox) {
    uiStore.highlightPdf(ref.page_num, ref.bbox)
  }
}

function getBlockIcon(type?: string) {
  switch (type) {
    case 'title': return '📑'
    case 'text': return '📝'
    case 'image': return '🖼️'
    case 'table': return '📊'
    case 'equation': return '🔢'
    default: return '📄'
  }
}
</script>

<template>
  <div class="block-list">
    <!-- 选中的节点 -->
    <div v-if="chatStore.selectedNodes.length" class="section">
      <h4 class="section-title">相关节点</h4>
      <div class="node-list">
        <div 
          v-for="node in chatStore.selectedNodes" 
          :key="node.node_id"
          class="node-item"
        >
          <span class="node-title">{{ node.title }}</span>
          <span v-if="node.relevance" class="node-relevance">
            {{ Math.round(node.relevance * 100) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 引用块 -->
    <div v-if="chatStore.references.length" class="section">
      <h4 class="section-title">引用来源</h4>
      <div class="refs-list">
        <div
          v-for="(ref, idx) in chatStore.references"
          :key="idx"
          class="ref-item"
          @click="handleBlockClick(ref)"
        >
          <div class="ref-header">
            <span class="ref-icon">{{ getBlockIcon(ref.block_type) }}</span>
            <span v-if="ref.page_num" class="ref-page">第 {{ ref.page_num }} 页</span>
          </div>
          <div class="ref-title">{{ ref.title || '引用块' }}</div>
          <div v-if="ref.context" class="ref-context">
            {{ ref.context.slice(0, 150) }}{{ ref.context.length > 150 ? '...' : '' }}
          </div>
          <div v-if="ref.reason" class="ref-reason">
            <span class="reason-label">原因:</span> {{ ref.reason }}
          </div>
        </div>
      </div>
    </div>

    <!-- 位置信息 -->
    <div v-if="chatStore.locations.length" class="section">
      <h4 class="section-title">PDF 位置</h4>
      <div class="location-list">
        <div
          v-for="loc in chatStore.locations"
          :key="loc.node_id"
          class="location-item"
        >
          <div class="loc-header">
            <span class="loc-title">{{ loc.title }}</span>
            <span v-if="loc.page_range" class="loc-pages">
              P{{ loc.page_range[0] }}-{{ loc.page_range[1] }}
            </span>
          </div>
          <div class="loc-blocks">
            <button
              v-if="loc.title_block"
              class="loc-block"
              @click="uiStore.highlightPdf(loc.title_block.page_num, loc.title_block.bbox)"
            >
              标题 @ P{{ loc.title_block.page_num }}
            </button>
            <button
              v-for="(block, idx) in loc.content_blocks?.slice(0, 3)"
              :key="idx"
              class="loc-block"
              @click="uiStore.highlightPdf(block.page_num, block.bbox)"
            >
              内容 @ P{{ block.page_num }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.block-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}

.node-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.node-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.node-title {
  font-size: 13px;
  color: var(--text-primary);
}

.node-relevance {
  font-size: 11px;
  font-weight: 600;
  color: var(--success);
  background: rgba(34, 197, 94, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.refs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ref-item {
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  
  &:hover {
    background: var(--bg-elevated);
    transform: translateX(2px);
  }
}

.ref-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.ref-icon {
  font-size: 14px;
}

.ref-page {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 10px;
}

.ref-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.ref-context {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.ref-reason {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-muted);
}

.reason-label {
  font-weight: 500;
}

.location-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.location-item {
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.loc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.loc-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.loc-pages {
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
}

.loc-blocks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.loc-block {
  font-size: 11px;
  padding: 4px 10px;
  background: var(--bg-secondary);
  border-radius: 12px;
  color: var(--text-secondary);
  transition: all 0.15s ease;
  
  &:hover {
    background: var(--primary);
    color: white;
  }
}
</style>
