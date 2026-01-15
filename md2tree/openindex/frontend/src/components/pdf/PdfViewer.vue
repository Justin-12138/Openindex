<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useDocumentStore, useUIStore, useChatStore } from '@/stores'
import * as pdfjsLib from 'pdfjs-dist'
import IconZoomIn from '../icons/IconZoomIn.vue'
import IconZoomOut from '../icons/IconZoomOut.vue'
import LoadingSpinner from '../common/LoadingSpinner.vue'

// Polyfill for Promise.withResolvers (required by pdfjs-dist v4.4+)
if (typeof Promise.withResolvers === 'undefined') {
  // @ts-ignore
  Promise.withResolvers = function () {
    let resolve, reject
    const promise = new Promise((res, rej) => {
      resolve = res
      reject = rej
    })
    return { promise, resolve, reject }
  }
}

// 配置 PDF.js worker - 使用 CDN 确保兼容性
// PDF.js 3.x 使用 .js 扩展名，4.x 使用 .mjs
const workerExt = pdfjsLib.version.startsWith('3.') ? 'js' : 'mjs'
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.${workerExt}`

// cmap 路径（使用 CDN 以确保兼容性）
const cMapUrl = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/cmaps/`

const docStore = useDocumentStore()
const uiStore = useUIStore()
const chatStore = useChatStore()

// 状态 - 使用普通变量存储PDF文档，避免Vue响应式干扰
const containerRef = ref<HTMLDivElement | null>(null)
let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null // 使用普通变量
const renderedPages = ref<Set<number>>(new Set())
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1.2)
const loading = ref(false)
const error = ref<string | null>(null)

// 高亮状态
const highlightBoxes = ref<Array<{ page: number; bbox: number[]; id: string }>>([])

// 加载 PDF
async function loadPdf(url: string) {
  loading.value = true
  error.value = null
  renderedPages.value.clear()

  // 清理之前的PDF文档对象
  if (pdfDoc) {
    try {
      pdfDoc.destroy()
    } catch (e) {
      console.warn('[PDF] Failed to destroy previous PDF document:', e)
    }
  }

  pdfDoc = null
  totalPages.value = 0
  
  try {
    console.log('[PDF] Loading PDF from:', url)
    console.log('[PDF] PDF.js version:', pdfjsLib.version)
    
    // 使用 fetch 获取完整 PDF 数据，避免 Range 请求问题
    console.log('[PDF] Fetching PDF data...')
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to fetch PDF: ${response.status} ${response.statusText}`)
    }
    
    const arrayBuffer = await response.arrayBuffer()
    console.log('[PDF] PDF data fetched, size:', arrayBuffer.byteLength, 'bytes')
    
    // 使用 URL 加载 PDF（更稳定）
    const loadingTask = pdfjsLib.getDocument({
      url: url,
      cMapUrl,
      cMapPacked: true,
      disableFontFace: false,
      disableRange: true,
      disableStream: true,
      disableAutoFetch: true,
    })
    
    loadingTask.onProgress = (progress: { loaded: number; total: number }) => {
      if (progress.total > 0) {
        console.log('[PDF] Parsing progress:', Math.round((progress.loaded / progress.total) * 100) + '%')
      }
    }
    
    const doc = await loadingTask.promise
    console.log('[PDF] Document loaded, pages:', doc.numPages)
    totalPages.value = doc.numPages
    pdfDoc = doc // 直接赋值到普通变量
    console.log('[PDF] Set totalPages to:', totalPages.value)

    // 强制触发Vue响应式更新
    await nextTick()
    loading.value = false
    console.log('[PDF] Set loading to false, totalPages:', totalPages.value)

    // 强制Vue重新渲染模板
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()

    // 再次等待canvas元素出现
    const maxRetries = 20
    let retries = 0
    while (retries < maxRetries) {
      const canvases = document.querySelectorAll('canvas')
      console.log(`[PDF] Canvas check ${retries + 1}: found ${canvases.length}, expected ${totalPages.value}`)
      if (canvases.length >= totalPages.value) {
        console.log('[PDF] All canvas elements found!')
        break
      }
      await new Promise(resolve => setTimeout(resolve, 50))
      retries++
    }


    // 渲染第一页和可见页面
    console.log('[PDF] Starting to render pages...')

    // 使用setTimeout确保DOM完全渲染
    setTimeout(async () => {
      await renderVisiblePages()
    }, 100)
  } catch (e: unknown) {
    console.error('[PDF] Failed to load PDF:', e)
    error.value = (e as Error).message || '加载 PDF 失败'
  } finally {
    loading.value = false
  }
}

// 渲染单页
async function renderPage(pageNum: number) {
  if (!pdfDoc) {
    console.warn(`[PDF] Cannot render page ${pageNum}: pdfDoc missing`)
    return
  }
  if (renderedPages.value.has(pageNum)) {
    console.log(`[PDF] Page ${pageNum} already rendered, skipping`)
    return
  }

  // 直接使用 document.querySelector 查找canvas，避免Vue ref问题
  const canvasEl = document.querySelector(`canvas[data-page="${pageNum}"]`) as HTMLCanvasElement | null
  if (!canvasEl) {
    console.warn(`[PDF] Canvas not found for page ${pageNum}, total canvases:`, document.querySelectorAll('canvas').length)
    return
  }
  
  try {
    console.log(`[PDF] Rendering page ${pageNum}...`)
    const page = await pdfDoc!.getPage(pageNum)
    const viewport = page.getViewport({ scale: scale.value })
    
    const context = canvasEl.getContext('2d', { alpha: false })
    if (!context) {
      console.error('[PDF] Failed to get 2d context')
      return
    }
    
    // 设置 canvas 尺寸 - 简化处理，避免复杂的像素比缩放
    canvasEl.width = viewport.width
    canvasEl.height = viewport.height

    // 设置 canvas 显示尺寸
    canvasEl.style.width = `${viewport.width}px`
    canvasEl.style.height = `${viewport.height}px`

    // 先填充白色背景（防止透明问题导致棋盘格）
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, viewport.width, viewport.height)

    // 重置变换矩阵
    context.setTransform(1, 0, 0, 1, 0, 0)
    
    console.log(`[PDF] Canvas size: ${canvasEl.width}x${canvasEl.height}, viewport: ${viewport.width}x${viewport.height}`)
    
    // 渲染页面
    const renderTask = page.render({
      canvasContext: context,
      viewport: viewport,
    })
    
    await renderTask.promise
    renderedPages.value.add(pageNum)
    console.log(`[PDF] Page ${pageNum} rendered successfully`)
  } catch (e) {
    console.error(`[PDF] Failed to render page ${pageNum}:`, e)
  }
}

// 渲染可见页面
async function renderVisiblePages() {
  if (!pdfDoc) {
    console.warn('[PDF] renderVisiblePages: pdfDoc missing')
    return
  }

  const container = containerRef.value || document.querySelector('.pdf-container') as HTMLElement
  if (!container) {
    console.warn('[PDF] renderVisiblePages: container not found')
    return
  }

  const scrollTop = container.scrollTop
  const viewportHeight = container.clientHeight || 800 // 默认高度

  console.log(`[PDF] Container: scrollTop=${scrollTop}, viewportHeight=${viewportHeight}`)

  // 估算页面高度 (A4 比例)
  const estimatedPageHeight = 842 * scale.value + 16 // 加上 gap

  // 始终从第1页开始，确保首页被渲染
  const startPage = Math.max(1, Math.floor(scrollTop / estimatedPageHeight))
  const endPage = Math.min(totalPages.value, Math.ceil((scrollTop + viewportHeight) / estimatedPageHeight) + 2)

  console.log(`[PDF] Rendering pages ${startPage} to ${endPage}`)

  // 确保第一页总是被渲染
  if (!renderedPages.value.has(1)) {
    await renderPage(1)
  }

  // 渲染范围内的页面（限制并发，避免阻塞）
  const pagesToRender = []
  for (let i = startPage; i <= endPage; i++) {
    if (!renderedPages.value.has(i)) {
      pagesToRender.push(i)
    }
  }

  // 逐个渲染页面，确保顺序
  for (const pageNum of pagesToRender) {
    await renderPage(pageNum)
  }
}

// 监听滚动
let scrollTimeout: number | null = null
function handleScroll() {
  if (!containerRef.value) return
  
  const container = containerRef.value
  const pageElements = container.querySelectorAll('.pdf-page')
  
  // 计算当前页
  let foundPage = 1
  const containerRect = container.getBoundingClientRect()
  for (let i = 0; i < pageElements.length; i++) {
    const pageEl = pageElements[i]
    if (!pageEl) continue
    const rect = pageEl.getBoundingClientRect()
    if (rect.top <= containerRect.top + containerRect.height / 2) {
      foundPage = i + 1
    }
  }
  currentPage.value = foundPage
  
  // 防抖懒加载渲染
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
  }
  scrollTimeout = window.setTimeout(() => {
    renderVisiblePages()
  }, 100)
}

// 缩放
async function zoomIn() {
  if (scale.value < 2.5) {
    scale.value = Math.min(2.5, scale.value + 0.2)
    await rerender()
  }
}

async function zoomOut() {
  if (scale.value > 0.5) {
    scale.value = Math.max(0.5, scale.value - 0.2)
    await rerender()
  }
}

async function setScale(newScale: number) {
  scale.value = newScale
  await rerender()
}

// 重新渲染所有页面
async function rerender() {
  renderedPages.value.clear()
  await nextTick()
  await renderVisiblePages()
}

// 跳转到页面
function goToPage(pageNum: number) {
  if (!containerRef.value || pageNum < 1 || pageNum > totalPages.value) return
  
  const pageElement = containerRef.value.querySelector(`[data-page="${pageNum}"].pdf-page`)
  if (pageElement) {
    pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 高亮区域
function highlightArea(page: number, bbox: number[], duration = 3000) {
  // 先跳转到页面
  goToPage(page)
  
  const id = `${page}-${bbox.join('-')}-${Date.now()}`
  highlightBoxes.value.push({ page, bbox, id })
  
  if (duration > 0) {
    setTimeout(() => {
      highlightBoxes.value = highlightBoxes.value.filter(h => h.id !== id)
    }, duration)
  }
}

// 获取高亮样式
function getHighlightStyle(bbox: number[]) {
  const x0 = bbox[0] ?? 0
  const y0 = bbox[1] ?? 0
  const x1 = bbox[2] ?? 0
  const y1 = bbox[3] ?? 0
  
  return {
    left: `${x0 * scale.value}px`,
    top: `${y0 * scale.value}px`,
    width: `${(x1 - x0) * scale.value}px`,
    height: `${(y1 - y0) * scale.value}px`
  }
}

// 监听 PDF URL 变化
watch(() => docStore.pdfUrl, (url) => {
  console.log('PDF URL changed:', url)
  if (url) {
    loadPdf(url)
  }
}, { immediate: true })

// 监听高亮请求
watch(() => uiStore.pdfHighlight, (highlight) => {
  if (highlight) {
    highlightArea(highlight.page, highlight.bbox)
  }
})

// 监听引用点击 - 只显示当前文档的标注
watch(() => chatStore.locations, (locs) => {
  // 清除旧高亮
  highlightBoxes.value = []
  
  // 只有当 PDF 已加载且 locations 存在时才添加高亮
  // 确保 locations 属于当前文档（通过检查 PDF URL 是否匹配）
  if (!pdfDoc || !docStore.pdfUrl) {
    return
  }
  
  // 添加新高亮
  locs.forEach(loc => {
    if (loc.title_block) {
      highlightArea(loc.title_block.page_num, loc.title_block.bbox, 0)
    }
    loc.content_blocks?.forEach(block => {
      highlightArea(block.page_num, block.bbox, 0)
    })
  })
}, { deep: true })

// 监听文档切换，清空高亮
watch(() => docStore.pdfUrl, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl) {
    // PDF 切换时，清空所有高亮
    highlightBoxes.value = []
  }
})

// 生命周期
onMounted(() => {
  containerRef.value?.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  containerRef.value?.removeEventListener('scroll', handleScroll)
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
  }
})

// 暴露方法给父组件
defineExpose({
  goToPage,
  highlightArea,
  zoomIn,
  zoomOut
})
</script>

<template>
  <div class="pdf-viewer">
    <!-- 工具栏 -->
    <div class="pdf-toolbar">
      <div class="page-nav">
        <input 
          type="number" 
          :value="currentPage"
          :min="1"
          :max="totalPages"
          @change="(e) => goToPage(parseInt((e.target as HTMLInputElement).value))"
          class="page-input"
        />
        <span class="page-separator">/</span>
        <span class="total-pages">{{ totalPages }}</span>
      </div>
      
      <div class="zoom-controls">
        <button class="icon-btn" @click="zoomOut" :disabled="scale <= 0.5" title="缩小">
          <IconZoomOut />
        </button>
        <select :value="Math.round(scale * 100)" @change="(e) => setScale(parseInt((e.target as HTMLSelectElement).value) / 100)" class="zoom-select">
          <option value="50">50%</option>
          <option value="75">75%</option>
          <option value="100">100%</option>
          <option value="120">120%</option>
          <option value="150">150%</option>
          <option value="200">200%</option>
        </select>
        <button class="icon-btn" @click="zoomIn" :disabled="scale >= 2.5" title="放大">
          <IconZoomIn />
        </button>
      </div>
      
      <div class="doc-name truncate">
        {{ docStore.currentDoc?.name }}
      </div>
    </div>

    <!-- PDF 内容 -->
    <div ref="containerRef" class="pdf-container">
      <div v-if="loading" class="pdf-loading">
        <LoadingSpinner text="加载 PDF..." />
      </div>
      
      <div v-else-if="error" class="pdf-error">
        <span class="error-icon">⚠️</span>
        <p>{{ error }}</p>
        <button class="btn btn-primary" @click="loadPdf(docStore.pdfUrl!)">重试</button>
      </div>

      <template v-else-if="totalPages > 0">
        <div
          v-for="pageNum in Array.from({ length: totalPages }, (_, i) => i + 1)"
          :key="pageNum"
          :data-page="pageNum"
          class="pdf-page"
        >
          <canvas :data-page="pageNum" :key="'canvas-' + pageNum" />
          
          <!-- 页码标签 -->
          <div class="page-label">{{ pageNum }}</div>
          
          <!-- 高亮覆盖层 -->
          <div
            v-for="highlight in highlightBoxes.filter(h => h.page === pageNum)"
            :key="highlight.id"
            class="highlight-box"
            :style="getHighlightStyle(highlight.bbox)"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
}

.pdf-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.page-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-input {
  width: 48px;
  text-align: center;
  padding: 4px;
  font-size: 13px;
  
  &::-webkit-inner-spin-button,
  &::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
}

.page-separator {
  color: var(--text-muted);
}

.total-pages {
  font-size: 13px;
  color: var(--text-secondary);
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.zoom-select {
  padding: 4px 8px;
  font-size: 13px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  cursor: pointer;
}

.doc-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: right;
}

.pdf-container {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  gap: 16px;
  background: #2d2d2d;
}

.pdf-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.pdf-page {
  position: relative;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  
  canvas {
    display: block;
  }
}

.page-label {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  opacity: 0;
  transition: opacity 0.2s ease;
  
  .pdf-page:hover & {
    opacity: 1;
  }
}

.highlight-box {
  position: absolute;
  background: rgba(251, 191, 36, 0.35);
  border: 2px solid rgba(251, 191, 36, 0.8);
  border-radius: 2px;
  pointer-events: none;
  animation: highlightPulse 2s ease-in-out infinite;
}

@keyframes highlightPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.pdf-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  text-align: center;
  height: 100%;
  
  .error-icon {
    font-size: 48px;
  }
  
  p {
    color: var(--text-secondary);
  }
}
</style>
