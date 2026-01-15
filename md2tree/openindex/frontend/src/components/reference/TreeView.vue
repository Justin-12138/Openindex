<script setup lang="ts">
import { ref } from 'vue'
import type { TreeNode } from '@/types'
import { useUIStore } from '@/stores'
import IconChevron from '../icons/IconChevron.vue'

defineProps<{
  nodes: TreeNode[]
  level?: number
}>()

const uiStore = useUIStore()
const expandedNodes = ref<Set<string>>(new Set())

function toggleNode(nodeId: string) {
  if (expandedNodes.value.has(nodeId)) {
    expandedNodes.value.delete(nodeId)
  } else {
    expandedNodes.value.add(nodeId)
  }
}

function isExpanded(nodeId: string) {
  return expandedNodes.value.has(nodeId)
}

function handleNodeClick(node: TreeNode) {
  // 如果有页面信息，跳转到 PDF
  if (node.page_info?.title_block) {
    const block = node.page_info.title_block
    uiStore.highlightPdf(block.page_num, block.bbox)
  }
}

function getNodeIcon(level?: number) {
  const icons = ['📄', '📑', '📌', '📍', '·']
  return icons[Math.min(level || 0, icons.length - 1)]
}
</script>

<template>
  <div class="tree-view" :class="`level-${level || 0}`">
    <div
      v-for="node in nodes"
      :key="node.node_id || node.title"
      class="tree-node"
    >
      <div 
        class="node-row"
        @click="handleNodeClick(node)"
      >
        <!-- 展开按钮 -->
        <button
          v-if="node.nodes?.length"
          class="expand-btn"
          @click.stop="toggleNode(node.node_id || node.title)"
        >
          <IconChevron 
            class="chevron"
            :class="{ expanded: isExpanded(node.node_id || node.title) }"
          />
        </button>
        <span v-else class="expand-placeholder"></span>
        
        <!-- 节点图标 -->
        <span class="node-icon">{{ getNodeIcon(level) }}</span>
        
        <!-- 节点标题 -->
        <span class="node-title">{{ node.title }}</span>
        
        <!-- 页码 -->
        <span v-if="node.page_info?.page_range" class="node-pages">
          P{{ node.page_info.page_range[0] }}
          <template v-if="node.page_info.page_range[1] !== node.page_info.page_range[0]">
            -{{ node.page_info.page_range[1] }}
          </template>
        </span>
      </div>
      
      <!-- 摘要 -->
      <div v-if="node.summary && isExpanded(node.node_id || node.title)" class="node-summary">
        {{ node.summary }}
      </div>
      
      <!-- 子节点 -->
      <div 
        v-if="node.nodes?.length && isExpanded(node.node_id || node.title)" 
        class="node-children"
      >
        <TreeView :nodes="node.nodes" :level="(level || 0) + 1" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.tree-view {
  font-size: 13px;
}

.tree-node {
  margin-bottom: 2px;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
  
  &:hover {
    background: var(--bg-tertiary);
  }
}

.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  
  &:hover {
    background: var(--bg-elevated);
  }
}

.chevron {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
  
  &.expanded {
    transform: rotate(90deg);
  }
}

.expand-placeholder {
  width: 20px;
}

.node-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.node-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-weight: 500;
}

.node-pages {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 8px;
  flex-shrink: 0;
}

.node-summary {
  margin: 4px 0 8px 28px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: 6px;
  line-height: 1.5;
  border-left: 2px solid var(--primary);
}

.node-children {
  margin-left: 16px;
  padding-left: 8px;
  border-left: 1px solid var(--border-subtle);
}

// 不同层级的缩进和样式
.level-0 > .tree-node > .node-row .node-title {
  font-size: 14px;
}

.level-1 > .tree-node > .node-row .node-title {
  font-size: 13px;
}

.level-2 > .tree-node > .node-row .node-title {
  font-size: 13px;
  font-weight: 400;
}
</style>
