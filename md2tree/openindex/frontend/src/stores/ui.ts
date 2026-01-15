import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useStorage } from '@vueuse/core'
import type { Toast, ToastType } from '@/types'

export const useUIStore = defineStore('ui', () => {
  // 面板可见性（持久化到 localStorage）
  const sidebarVisible = useStorage('openindex-sidebar', true)
  const pdfPanelVisible = useStorage('openindex-pdf', true)
  const refPanelVisible = useStorage('openindex-ref', true)

  // 面板宽度（持久化）
  const sidebarWidth = useStorage('openindex-sidebar-width', 280)
  const pdfPanelWidth = useStorage('openindex-pdf-width', 500)
  const refPanelWidth = useStorage('openindex-ref-width', 360)

  // 引用面板标签
  const refTab = ref<'blocks' | 'tree'>('blocks')

  // PDF 高亮请求
  const pdfHighlight = ref<{ page: number; bbox: number[] } | null>(null)

  // Toast 通知
  const toasts = ref<Toast[]>([])
  let toastId = 0

  // 方法
  function toggleSidebar() {
    sidebarVisible.value = !sidebarVisible.value
  }

  function togglePdfPanel() {
    pdfPanelVisible.value = !pdfPanelVisible.value
  }

  function toggleRefPanel() {
    refPanelVisible.value = !refPanelVisible.value
  }

  function setRefTab(tab: 'blocks' | 'tree') {
    refTab.value = tab
  }

  function highlightPdf(page: number, bbox: number[]) {
    pdfHighlight.value = { page, bbox }
    // 3 秒后清除
    setTimeout(() => {
      if (pdfHighlight.value?.page === page) {
        pdfHighlight.value = null
      }
    }, 3000)
  }

  function showToast(message: string, type: ToastType = 'info', duration = 3000) {
    const toast: Toast = {
      id: ++toastId,
      type,
      message,
      duration
    }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        removeToast(toast.id)
      }, duration)
    }

    return toast.id
  }

  function removeToast(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  // 快捷键处理
  function handleKeyboard(e: KeyboardEvent) {
    // Ctrl/Cmd + 1/2/3 切换面板
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey) {
      switch (e.key) {
        case '1':
          e.preventDefault()
          toggleSidebar()
          break
        case '2':
          e.preventDefault()
          togglePdfPanel()
          break
        case '3':
          e.preventDefault()
          toggleRefPanel()
          break
      }
    }
  }

  return {
    // 状态
    sidebarVisible,
    pdfPanelVisible,
    refPanelVisible,
    sidebarWidth,
    pdfPanelWidth,
    refPanelWidth,
    refTab,
    pdfHighlight,
    toasts,
    // 方法
    toggleSidebar,
    togglePdfPanel,
    toggleRefPanel,
    setRefTab,
    highlightPdf,
    showToast,
    removeToast,
    handleKeyboard
  }
})
