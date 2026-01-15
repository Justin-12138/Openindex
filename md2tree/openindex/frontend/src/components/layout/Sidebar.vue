<script setup lang="ts">
import { ref } from 'vue'
import { useLibraryStore, useDocumentStore, useUIStore, useChatStore } from '@/stores'
import type { Document, Library } from '@/types'
import IconPlus from '../icons/IconPlus.vue'
import IconFolder from '../icons/IconFolder.vue'
import IconChevron from '../icons/IconChevron.vue'
import IconFile from '../icons/IconFile.vue'
import IconTrash from '../icons/IconTrash.vue'
import IconUpload from '../icons/IconUpload.vue'

const libraryStore = useLibraryStore()
const docStore = useDocumentStore()
const chatStore = useChatStore()
const uiStore = useUIStore()

const newLibraryName = ref('')
const showNewLibrary = ref(false)
const dragOverTarget = ref<string | null>(null)

// 上传文件
const fileInput = ref<HTMLInputElement | null>(null)

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  
  try {
    uiStore.showToast('正在上传...', 'loading', 0)
    await libraryStore.uploadDocument(file)
    uiStore.showToast('上传成功', 'success')
  } catch (err: any) {
    uiStore.showToast(err.message || '上传失败', 'error')
  }
  
  target.value = ''
}

// 选择文档
async function selectDoc(doc: Document) {
  // selectDocument 内部已经会加载对话，这里不需要重复调用
  await docStore.selectDocument(doc)
}

// 删除文档
async function deleteDoc(doc: Document, e: Event) {
  e.stopPropagation()
  if (!confirm(`确定删除 "${doc.name}"？\n相关的对话记录也会被删除。`)) return
  
  try {
    await libraryStore.deleteDocument(doc.id)
    if (docStore.currentDoc?.id === doc.id) {
      docStore.clearDocument()
      chatStore.clearChat()
    }
    uiStore.showToast('已删除', 'success')
  } catch (err: any) {
    uiStore.showToast(err.message || '删除失败', 'error')
  }
}

// 创建库
async function createLibrary() {
  if (!newLibraryName.value.trim()) return
  
  try {
    await libraryStore.createLibrary(newLibraryName.value.trim())
    newLibraryName.value = ''
    showNewLibrary.value = false
    uiStore.showToast('库已创建', 'success')
  } catch (err: any) {
    uiStore.showToast(err.message || '创建失败', 'error')
  }
}

// 删除库
async function deleteLibrary(lib: Library, e: Event) {
  e.stopPropagation()
  if (!confirm(`确定删除库 "${lib.name}"？\n文档将移至未分类。`)) return
  
  try {
    await libraryStore.deleteLibrary(lib.id)
    uiStore.showToast('库已删除', 'success')
  } catch (err: any) {
    uiStore.showToast(err.message || '删除失败', 'error')
  }
}

// 拖放
function handleDragStart(e: DragEvent, doc: Document) {
  e.dataTransfer?.setData('docId', doc.id)
}

function handleDragOver(e: DragEvent, targetId: string) {
  e.preventDefault()
  dragOverTarget.value = targetId
}

function handleDragLeave() {
  dragOverTarget.value = null
}

async function handleDrop(e: DragEvent, libraryId: string | null) {
  e.preventDefault()
  dragOverTarget.value = null
  
  const docId = e.dataTransfer?.getData('docId')
  if (!docId) return
  
  try {
    await libraryStore.moveDocument(docId, libraryId)
    uiStore.showToast('文档已移动', 'success')
  } catch (err: any) {
    uiStore.showToast(err.message || '移动失败', 'error')
  }
}

// 状态颜色
function getStatusClass(status: string) {
  switch (status) {
    case 'ready': return 'status-ready'
    case 'parsing': return 'status-parsing'
    case 'error': return 'status-error'
    default: return 'status-pending'
  }
}
</script>

<template>
  <div class="sidebar">
    <!-- 头部 -->
    <div class="sidebar-header">
      <h1 class="logo">
        <span class="logo-icon">📚</span>
        OpenIndex
      </h1>
      <button class="icon-btn" @click="triggerUpload" title="上传 PDF">
        <IconUpload />
      </button>
      <input 
        ref="fileInput" 
        type="file" 
        accept=".pdf" 
        hidden 
        @change="handleFileChange"
      />
    </div>

    <!-- 库列表 -->
    <div class="library-list">
      <!-- 库 -->
      <div
        v-for="lib in libraryStore.libraries"
        :key="lib.id"
        class="library-group"
      >
        <div 
          class="library-header"
          :class="{ 'drag-over': dragOverTarget === lib.id }"
          @click="libraryStore.toggleLibrary(lib.id)"
          @dragover="(e) => handleDragOver(e, lib.id)"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, lib.id)"
        >
          <IconChevron 
            class="chevron" 
            :class="{ expanded: libraryStore.isExpanded(lib.id) }" 
          />
          <span class="lib-icon">{{ lib.icon || '📁' }}</span>
          <span class="lib-name truncate">{{ lib.name }}</span>
          <span class="lib-count">{{ libraryStore.getLibraryDocs(lib.id).length }}</span>
          <button 
            class="icon-btn delete-btn" 
            @click="(e) => deleteLibrary(lib, e)"
            title="删除库"
          >
            <IconTrash />
          </button>
        </div>
        
        <div v-if="libraryStore.isExpanded(lib.id)" class="doc-list">
          <div
            v-for="doc in libraryStore.getLibraryDocs(lib.id)"
            :key="doc.id"
            class="doc-item"
            :class="{ active: docStore.currentDoc?.id === doc.id }"
            draggable="true"
            @click="selectDoc(doc)"
            @dragstart="(e) => handleDragStart(e, doc)"
          >
            <IconFile class="doc-icon" />
            <span class="doc-name truncate">{{ doc.name }}</span>
            <span class="status-dot" :class="getStatusClass(doc.status)" />
            <button 
              class="icon-btn delete-btn" 
              @click="(e) => deleteDoc(doc, e)"
              title="删除文档"
            >
              <IconTrash />
            </button>
          </div>
        </div>
      </div>

      <!-- 未分类 -->
      <div class="library-group">
        <div 
          class="library-header"
          :class="{ 'drag-over': dragOverTarget === 'uncategorized' }"
          @click="libraryStore.toggleLibrary('uncategorized')"
          @dragover="(e) => handleDragOver(e, 'uncategorized')"
          @dragleave="handleDragLeave"
          @drop="(e) => handleDrop(e, null)"
        >
          <IconChevron 
            class="chevron" 
            :class="{ expanded: libraryStore.isExpanded('uncategorized') }" 
          />
          <IconFolder class="lib-icon-svg" />
          <span class="lib-name truncate">未分类</span>
          <span class="lib-count">{{ libraryStore.uncategorizedDocs.length }}</span>
        </div>
        
        <div v-if="libraryStore.isExpanded('uncategorized')" class="doc-list">
          <div
            v-for="doc in libraryStore.uncategorizedDocs"
            :key="doc.id"
            class="doc-item"
            :class="{ active: docStore.currentDoc?.id === doc.id }"
            draggable="true"
            @click="selectDoc(doc)"
            @dragstart="(e) => handleDragStart(e, doc)"
          >
            <IconFile class="doc-icon" />
            <span class="doc-name truncate">{{ doc.name }}</span>
            <span class="status-dot" :class="getStatusClass(doc.status)" />
            <button 
              class="icon-btn delete-btn" 
              @click="(e) => deleteDoc(doc, e)"
              title="删除文档"
            >
              <IconTrash />
            </button>
          </div>
          
          <div v-if="libraryStore.uncategorizedDocs.length === 0" class="empty-hint">
            拖动文档到这里
          </div>
        </div>
      </div>

      <!-- 新建库 -->
      <div v-if="showNewLibrary" class="new-library-form">
        <input
          v-model="newLibraryName"
          type="text"
          placeholder="库名称"
          @keyup.enter="createLibrary"
          @keyup.esc="showNewLibrary = false"
          autofocus
        />
        <button class="btn btn-primary btn-sm" @click="createLibrary">创建</button>
        <button class="btn btn-ghost btn-sm" @click="showNewLibrary = false">取消</button>
      </div>
      
      <button 
        v-else
        class="add-library-btn"
        @click="showNewLibrary = true"
      >
        <IconPlus />
        新建库
      </button>
    </div>

    <!-- 底部统计 -->
    <div class="sidebar-footer">
      <span class="stat">{{ libraryStore.totalDocuments }} 文档</span>
      <span class="divider">·</span>
      <span class="stat">{{ libraryStore.libraries.length }} 库</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  
  .logo-icon {
    font-size: 20px;
  }
}

.library-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.library-group {
  margin-bottom: 4px;
}

.library-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
  
  &:hover {
    background: var(--bg-tertiary);
    
    .delete-btn {
      opacity: 1;
    }
  }
  
  &.drag-over {
    background: rgba(59, 130, 246, 0.15);
    outline: 2px dashed var(--primary);
  }
}

.chevron {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
  
  &.expanded {
    transform: rotate(90deg);
  }
}

.lib-icon {
  font-size: 16px;
}

.lib-icon-svg {
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
}

.lib-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.lib-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 10px;
}

.delete-btn {
  opacity: 0;
  width: 24px;
  height: 24px;
  
  &:hover {
    color: var(--error);
    background: rgba(239, 68, 68, 0.1);
  }
}

.doc-list {
  padding-left: 20px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
  
  &:hover {
    background: var(--bg-tertiary);
    
    .delete-btn {
      opacity: 1;
    }
  }
  
  &.active {
    background: rgba(59, 130, 246, 0.15);
    
    .doc-name {
      color: var(--primary);
    }
  }
}

.doc-icon {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.doc-name {
  flex: 1;
  font-size: 13px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  
  &.status-ready { background: var(--success); }
  &.status-parsing { background: var(--warning); animation: pulse 2s infinite; }
  &.status-error { background: var(--error); }
  &.status-pending { background: var(--text-muted); }
}

.empty-hint {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 16px;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  margin: 4px;
}

.new-library-form {
  display: flex;
  gap: 8px;
  padding: 8px;
  
  input {
    flex: 1;
    min-width: 0;
  }
}

.add-library-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  margin: 8px;
  color: var(--text-secondary);
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  transition: all 0.15s ease;
  
  &:hover {
    color: var(--primary);
    border-color: var(--primary);
    background: rgba(59, 130, 246, 0.05);
  }
  
  svg {
    width: 16px;
    height: 16px;
  }
}

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--border-subtle);
  font-size: 12px;
  color: var(--text-muted);
}

.divider {
  opacity: 0.5;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
