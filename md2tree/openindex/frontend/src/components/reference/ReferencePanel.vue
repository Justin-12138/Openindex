<script setup lang="ts">
import { computed } from 'vue'
import { useUIStore, useChatStore, useDocumentStore } from '@/stores'
import TreeView from './TreeView.vue'
import BlockList from './BlockList.vue'

const uiStore = useUIStore()
const chatStore = useChatStore()
const docStore = useDocumentStore()

const hasReferences = computed(() => 
  chatStore.references.length > 0 || 
  chatStore.selectedNodes.length > 0
)
</script>

<template>
  <div class="reference-panel">
    <!-- 头部 -->
    <div class="panel-header">
      <div class="tabs">
        <button 
          class="tab" 
          :class="{ active: uiStore.refTab === 'blocks' }"
          @click="uiStore.setRefTab('blocks')"
        >
          <span class="tab-icon">📎</span>
          引用
          <span v-if="chatStore.references.length" class="tab-badge">
            {{ chatStore.references.length }}
          </span>
        </button>
        <button 
          class="tab" 
          :class="{ active: uiStore.refTab === 'tree' }"
          @click="uiStore.setRefTab('tree')"
        >
          <span class="tab-icon">🌳</span>
          结构
        </button>
      </div>
    </div>

    <!-- 内容 -->
    <div class="panel-content">
      <template v-if="uiStore.refTab === 'blocks'">
        <BlockList v-if="hasReferences" />
        <div v-else class="empty-refs">
          <span class="empty-icon">📎</span>
          <p>提问后将显示相关引用</p>
        </div>
      </template>
      
      <template v-else>
        <TreeView v-if="docStore.treeData" :nodes="docStore.treeData" />
        <div v-else class="empty-refs">
          <span class="empty-icon">🌳</span>
          <p>选择已解析的文档查看结构</p>
        </div>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.reference-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: 12px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  padding: 4px;
}

.tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  border-radius: 6px;
  transition: all 0.15s ease;
  
  &:hover {
    color: var(--text-primary);
  }
  
  &.active {
    background: var(--bg-elevated);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
  }
}

.tab-icon {
  font-size: 14px;
}

.tab-badge {
  background: var(--primary);
  color: white;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-refs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-muted);
  text-align: center;
  
  .empty-icon {
    font-size: 36px;
    margin-bottom: 12px;
    opacity: 0.6;
  }
  
  p {
    font-size: 13px;
  }
}
</style>
