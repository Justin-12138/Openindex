<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useLibraryStore, useUIStore } from './stores'
import MainLayout from './components/layout/MainLayout.vue'
import ToastContainer from './components/common/ToastContainer.vue'

const libraryStore = useLibraryStore()
const uiStore = useUIStore()

// 初始化加载
onMounted(async () => {
  try {
    await libraryStore.loadAll()
    
    // 恢复之前选择的文档和对话
    const { useDocumentStore } = await import('./stores/document')
    const docStore = useDocumentStore()
    await docStore.restoreDocument()
  } catch (e) {
    console.error('Failed to load initial data:', e)
    uiStore.showToast('加载数据失败', 'error')
  }
  
  // 注册快捷键
  window.addEventListener('keydown', uiStore.handleKeyboard)
})

onUnmounted(() => {
  window.removeEventListener('keydown', uiStore.handleKeyboard)
})
</script>

<template>
  <MainLayout />
  <ToastContainer />
</template>
