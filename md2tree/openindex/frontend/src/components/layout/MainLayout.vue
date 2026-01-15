<script setup lang="ts">
import { computed } from 'vue'
import { useUIStore, useDocumentStore } from '@/stores'
import Sidebar from './Sidebar.vue'
import PanelResizer from './PanelResizer.vue'
import PdfViewer from '../pdf/PdfViewer.vue'
import ChatPanel from '../chat/ChatPanel.vue'
import ReferencePanel from '../reference/ReferencePanel.vue'
import EmptyState from '../common/EmptyState.vue'

const uiStore = useUIStore()
const docStore = useDocumentStore()

// 计算各面板样式
const sidebarStyle = computed(() => ({
  width: uiStore.sidebarVisible ? `${uiStore.sidebarWidth}px` : '0px',
  minWidth: uiStore.sidebarVisible ? '220px' : '0px'
}))

const pdfStyle = computed(() => ({
  width: uiStore.pdfPanelVisible ? `${uiStore.pdfPanelWidth}px` : '0px',
  minWidth: uiStore.pdfPanelVisible ? '300px' : '0px'
}))

const refStyle = computed(() => ({
  width: uiStore.refPanelVisible ? `${uiStore.refPanelWidth}px` : '0px',
  minWidth: uiStore.refPanelVisible ? '280px' : '0px'
}))

// 拖拽调整大小
function handleSidebarResize(delta: number) {
  uiStore.sidebarWidth = Math.max(220, Math.min(400, uiStore.sidebarWidth + delta))
}

function handlePdfResize(delta: number) {
  uiStore.pdfPanelWidth = Math.max(300, Math.min(800, uiStore.pdfPanelWidth + delta))
}

function handleRefResize(delta: number) {
  uiStore.refPanelWidth = Math.max(280, Math.min(500, uiStore.refPanelWidth - delta))
}
</script>

<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar-panel" :style="sidebarStyle">
      <Sidebar v-if="uiStore.sidebarVisible" />
    </aside>
    
    <PanelResizer 
      v-if="uiStore.sidebarVisible" 
      @resize="handleSidebarResize" 
    />

    <!-- PDF 面板 -->
    <section class="pdf-panel" :style="pdfStyle">
      <PdfViewer v-if="uiStore.pdfPanelVisible && docStore.currentDoc" />
      <EmptyState 
        v-else-if="uiStore.pdfPanelVisible && !docStore.currentDoc"
        icon="📄"
        title="选择文档"
        description="从左侧选择一个 PDF 文档开始"
      />
    </section>
    
    <PanelResizer 
      v-if="uiStore.pdfPanelVisible && docStore.currentDoc" 
      @resize="handlePdfResize" 
    />

    <!-- 聊天面板 -->
    <section class="chat-panel">
      <ChatPanel v-if="docStore.currentDoc" />
      <EmptyState 
        v-else
        icon="💬"
        title="开始对话"
        description="选择文档后可以开始提问"
      />
    </section>

    <PanelResizer 
      v-if="uiStore.refPanelVisible" 
      @resize="handleRefResize" 
    />

    <!-- 引用面板 -->
    <aside class="ref-panel" :style="refStyle">
      <ReferencePanel v-if="uiStore.refPanelVisible" />
    </aside>
  </div>
</template>

<style lang="scss" scoped>
.main-layout {
  display: flex;
  height: 100%;
  background: var(--bg-primary);
  overflow: hidden;
}

.sidebar-panel {
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  overflow: hidden;
  transition: width 0.2s ease, min-width 0.2s ease;
}

.pdf-panel {
  flex-shrink: 0;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-subtle);
  overflow: hidden;
  transition: width 0.2s ease, min-width 0.2s ease;
  display: flex;
  flex-direction: column;
}

.chat-panel {
  flex: 1;
  min-width: 320px;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ref-panel {
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
  overflow: hidden;
  transition: width 0.2s ease, min-width 0.2s ease;
}
</style>
