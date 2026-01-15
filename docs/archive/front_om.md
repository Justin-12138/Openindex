# OpenIndex 前端优化计划

> 文档创建时间: 2026-01-12  
> **状态: ✅ Vue 3 重构已完成** (2026-01-12)

## 🎉 已完成工作

### Vue 3 项目结构

```
md2tree/openindex/frontend/
├── src/
│   ├── assets/styles/        # 全局样式 (SCSS)
│   │   ├── variables.scss    # 设计系统变量
│   │   └── global.scss       # 全局样式
│   ├── components/
│   │   ├── layout/           # 布局组件
│   │   │   ├── MainLayout.vue
│   │   │   ├── Sidebar.vue
│   │   │   └── PanelResizer.vue
│   │   ├── pdf/              # PDF 查看器
│   │   │   └── PdfViewer.vue
│   │   ├── chat/             # 聊天面板
│   │   │   ├── ChatPanel.vue
│   │   │   └── MessageBubble.vue
│   │   ├── reference/        # 引用面板
│   │   │   ├── ReferencePanel.vue
│   │   │   ├── BlockList.vue
│   │   │   └── TreeView.vue
│   │   ├── common/           # 通用组件
│   │   │   ├── ToastContainer.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   └── EmptyState.vue
│   │   └── icons/            # SVG 图标组件
│   ├── composables/
│   │   └── useApi.ts         # API 封装
│   ├── stores/               # Pinia 状态管理
│   │   ├── library.ts        # 文档库状态
│   │   ├── document.ts       # 当前文档状态
│   │   ├── chat.ts           # 对话状态
│   │   └── ui.ts             # UI 状态 (面板宽度、Toast)
│   ├── types/
│   │   └── index.ts          # TypeScript 类型定义
│   ├── App.vue
│   └── main.ts
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 主要功能
- ✅ **四栏可调节布局**: 侧边栏 + PDF + 聊天 + 引用
- ✅ **PDF.js 集成**: 懒加载渲染、缩放、页面导航
- ✅ **高亮联动**: 点击引用自动跳转并高亮 PDF 区域
- ✅ **文档库管理**: 创建/删除库、拖拽移动文档
- ✅ **Pinia 状态管理**: 响应式数据流
- ✅ **Toast 通知系统**: 操作反馈
- ✅ **深色主题**: Inter + JetBrains Mono 字体
- ✅ **键盘快捷键**: Ctrl+1/2/3 切换面板

### 技术栈
- Vue 3 + Composition API
- TypeScript
- Vite
- Pinia
- PDF.js
- SCSS

---

## 📊 原始现状分析

### 当前技术栈
- **纯 HTML/CSS/JS** - 无框架，单文件 (~2000 行)
- **字体**: Noto Serif SC + IBM Plex Mono
- **布局**: CSS Grid 三栏布局
- **主题**: 深色主题，科技感设计

### 现有功能
- ✅ 文档库管理（创建/删除/重命名）
- ✅ 文档上传/删除
- ✅ 拖拽移动文档到库
- ✅ AI 对话问答
- ✅ 引用来源展示（文本块/文档结构）
- ❌ **PDF 原文展示** - 缺失

### 当前问题

| 问题 | 严重性 | 描述 |
|------|--------|------|
| 无 PDF 预览 | 高 | 用户无法直接查看原文，需要外部打开 |
| 布局不够灵活 | 中 | 固定三栏，无法调整宽度 |
| 代码结构混乱 | 中 | 单文件 2000+ 行，难以维护 |
| 缺少动效 | 低 | 交互反馈不够流畅 |
| 移动端适配差 | 低 | 仅桌面端可用 |

---

## 🎯 优化目标

### 优先级 P0（必须）
1. **集成 PDF 查看器** - 内嵌展示原文，支持高亮定位
2. **优化整体布局** - 可调节面板宽度，支持隐藏/展开

### 优先级 P1（重要）
3. **重构代码结构** - 模块化 JS，拆分 CSS
4. **增强交互体验** - 加载动画、过渡效果、Toast 提示

### 优先级 P2（可选）
5. **响应式适配** - 支持平板/移动端
6. **主题切换** - 支持浅色主题

---

## 🏗️ 技术方案选型

### 框架对比

| 框架 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Vue 3 + Vite** | 响应式简单、中文生态好、SFC 单文件组件、Composition API 灵活 | 需要构建 | ⭐⭐⭐⭐⭐ |
| **React 18 + Vite** | 生态最大、Hooks 强大、TS 支持好 | JSX 学习成本、状态管理复杂 | ⭐⭐⭐⭐ |
| **Svelte** | 编译时框架、性能极佳、代码简洁 | 生态较小、招人难 | ⭐⭐⭐ |
| **原生 JS** | 无依赖、简单 | 代码量大、难维护 | ⭐⭐ |

### 🎯 推荐方案：Vue 3 + Vite + Pinia

**理由**：
1. **Vue 3 Composition API** - 逻辑复用方便，TypeScript 支持好
2. **Vite** - 极快的开发体验，HMR 热更新
3. **Pinia** - 官方状态管理，比 Vuex 更简洁
4. **中文生态** - 文档、社区资源丰富
5. **渐进式** - 可以按需引入功能

### 备选方案：React 18 + Vite

如果团队更熟悉 React，也是不错的选择：
- **React 18** - Concurrent 特性、Suspense
- **Zustand** - 轻量状态管理（比 Redux 简单）
- **TanStack Query** - 服务端状态管理

### PDF 查看器选型

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **vue-pdf-embed** | Vue 3 组件、简单易用 | 功能有限 | ⭐⭐⭐ |
| **@vue-office/pdf** | 功能丰富、支持高亮 | 文档较少 | ⭐⭐⭐⭐ |
| **PDF.js + Vue 封装** | 完全可控、功能完整 | 需要自己封装 | ⭐⭐⭐⭐⭐ |
| **react-pdf** | React 生态、稳定 | 仅限 React | ⭐⭐⭐⭐ |

### 推荐方案：PDF.js + Vue 3 自定义组件

**理由**：
1. 完全可控，可定制高亮、跳转等功能
2. 与 Vue 3 响应式系统深度集成
3. 支持 bbox 精确定位和高亮动画

---

## 🛠️ Vue 3 项目架构

### 项目结构

```
md2tree/openindex/
├── frontend/                    # Vue 3 前端项目
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.ts              # 入口文件
│   │   ├── App.vue              # 根组件
│   │   ├── assets/
│   │   │   ├── styles/
│   │   │   │   ├── variables.css
│   │   │   │   ├── base.css
│   │   │   │   └── transitions.css
│   │   │   └── fonts/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppHeader.vue
│   │   │   │   ├── Sidebar.vue
│   │   │   │   ├── SplitPane.vue     # 可拖拽分隔面板
│   │   │   │   └── StatusBar.vue
│   │   │   ├── library/
│   │   │   │   ├── LibraryList.vue
│   │   │   │   ├── LibraryItem.vue
│   │   │   │   └── DocumentItem.vue
│   │   │   ├── pdf/
│   │   │   │   ├── PdfViewer.vue     # PDF 查看器主组件
│   │   │   │   ├── PdfToolbar.vue
│   │   │   │   ├── PdfCanvas.vue
│   │   │   │   └── PdfThumbnails.vue
│   │   │   ├── chat/
│   │   │   │   ├── ChatPanel.vue
│   │   │   │   ├── MessageList.vue
│   │   │   │   ├── MessageItem.vue
│   │   │   │   ├── ChatInput.vue
│   │   │   │   └── LoadingDots.vue
│   │   │   ├── reference/
│   │   │   │   ├── ReferencePanel.vue
│   │   │   │   ├── ReferenceBlock.vue
│   │   │   │   └── TreeView.vue
│   │   │   └── common/
│   │   │       ├── Modal.vue
│   │   │       ├── Toast.vue
│   │   │       ├── Button.vue
│   │   │       ├── Input.vue
│   │   │       └── Skeleton.vue
│   │   ├── composables/          # 组合式函数
│   │   │   ├── useApi.ts         # API 调用
│   │   │   ├── usePdf.ts         # PDF 操作
│   │   │   ├── useToast.ts       # Toast 通知
│   │   │   ├── useKeyboard.ts    # 快捷键
│   │   │   └── useStorage.ts     # 本地存储
│   │   ├── stores/               # Pinia 状态管理
│   │   │   ├── index.ts
│   │   │   ├── library.ts        # 库和文档状态
│   │   │   ├── document.ts       # 当前文档状态
│   │   │   ├── chat.ts           # 对话状态
│   │   │   └── ui.ts             # UI 状态
│   │   ├── types/                # TypeScript 类型
│   │   │   ├── api.ts
│   │   │   ├── document.ts
│   │   │   └── chat.ts
│   │   └── utils/
│   │       ├── format.ts
│   │       └── pdf-highlight.ts
│   └── public/
│       └── pdf.worker.min.js     # PDF.js worker
├── static/                       # 构建输出（被 FastAPI 托管）
│   ├── index.html
│   └── assets/
└── app.py                        # FastAPI 后端（保持不变）
```

### 核心依赖

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "pdfjs-dist": "^4.0.0",
    "@vueuse/core": "^10.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "sass": "^1.69.0"
  }
}
```

### 状态管理 (Pinia)

```typescript
// stores/document.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Document, Library } from '@/types'
import { api } from '@/composables/useApi'

export const useDocumentStore = defineStore('document', () => {
  // 状态
  const libraries = ref<Library[]>([])
  const documents = ref<Document[]>([])
  const currentDoc = ref<Document | null>(null)
  const expandedLibraries = ref<Set<string>>(new Set())
  
  // 计算属性
  const uncategorizedDocs = computed(() => 
    documents.value.filter(d => !d.library_id)
  )
  
  const currentLibraryDocs = computed(() => {
    if (!currentDoc.value?.library_id) return uncategorizedDocs.value
    return documents.value.filter(d => d.library_id === currentDoc.value?.library_id)
  })
  
  // 方法
  async function loadLibraries() {
    libraries.value = await api.libraries.list()
  }
  
  async function loadDocuments() {
    documents.value = await api.documents.list()
  }
  
  async function selectDocument(docId: string) {
    currentDoc.value = documents.value.find(d => d.id === docId) || null
  }
  
  async function deleteDocument(docId: string) {
    await api.documents.delete(docId)
    documents.value = documents.value.filter(d => d.id !== docId)
    if (currentDoc.value?.id === docId) {
      currentDoc.value = null
    }
  }
  
  async function moveDocument(docId: string, libraryId: string | null) {
    await api.documents.move(docId, libraryId)
    const doc = documents.value.find(d => d.id === docId)
    if (doc) doc.library_id = libraryId
  }
  
  return {
    libraries,
    documents,
    currentDoc,
    expandedLibraries,
    uncategorizedDocs,
    currentLibraryDocs,
    loadLibraries,
    loadDocuments,
    selectDocument,
    deleteDocument,
    moveDocument
  }
})
```

### PDF 查看器组件

```vue
<!-- components/pdf/PdfViewer.vue -->
<template>
  <div class="pdf-viewer" v-if="pdfUrl">
    <!-- 工具栏 -->
    <PdfToolbar
      :current-page="currentPage"
      :total-pages="totalPages"
      :scale="scale"
      @prev="prevPage"
      @next="nextPage"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @fit-width="fitWidth"
    />
    
    <!-- PDF 内容区 -->
    <div 
      ref="containerRef"
      class="pdf-container"
      @scroll="onScroll"
    >
      <canvas ref="canvasRef" class="pdf-canvas" />
      
      <!-- 高亮层 -->
      <div class="highlight-layer">
        <div
          v-for="(hl, idx) in highlights"
          :key="idx"
          class="highlight-box"
          :class="{ active: hl.active }"
          :style="getHighlightStyle(hl)"
        />
      </div>
    </div>
  </div>
  
  <div v-else class="pdf-placeholder">
    <div class="placeholder-icon">📄</div>
    <p>选择文档查看 PDF</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import PdfToolbar from './PdfToolbar.vue'

const props = defineProps<{
  pdfUrl: string | null
  highlightBbox?: { page: number; bbox: number[] } | null
}>()

const emit = defineEmits<{
  (e: 'page-change', page: number): void
  (e: 'text-select', text: string, page: number): void
}>()

const containerRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()

const pdfDoc = ref<pdfjsLib.PDFDocumentProxy | null>(null)
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1.0)
const highlights = ref<Array<{ page: number; bbox: number[]; active?: boolean }>>([])

// 加载 PDF
async function loadPdf(url: string) {
  const doc = await pdfjsLib.getDocument(url).promise
  pdfDoc.value = doc
  totalPages.value = doc.numPages
  await renderPage(1)
}

// 渲染页面
async function renderPage(pageNum: number) {
  if (!pdfDoc.value || !canvasRef.value) return
  
  const page = await pdfDoc.value.getPage(pageNum)
  const viewport = page.getViewport({ scale: scale.value })
  
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')!
  
  canvas.width = viewport.width
  canvas.height = viewport.height
  
  await page.render({
    canvasContext: ctx,
    viewport
  }).promise
  
  currentPage.value = pageNum
  emit('page-change', pageNum)
}

// 跳转到指定页面并高亮
function goToPage(page: number, bbox?: number[]) {
  renderPage(page)
  if (bbox) {
    highlights.value = [{ page, bbox, active: true }]
    // 3 秒后移除高亮
    setTimeout(() => {
      highlights.value = highlights.value.filter(h => !h.active)
    }, 3000)
  }
}

// 计算高亮样式
function getHighlightStyle(hl: { bbox: number[] }) {
  const [x1, y1, x2, y2] = hl.bbox
  return {
    left: `${x1 * scale.value}px`,
    top: `${y1 * scale.value}px`,
    width: `${(x2 - x1) * scale.value}px`,
    height: `${(y2 - y1) * scale.value}px`
  }
}

// 翻页
function prevPage() {
  if (currentPage.value > 1) renderPage(currentPage.value - 1)
}

function nextPage() {
  if (currentPage.value < totalPages.value) renderPage(currentPage.value + 1)
}

// 缩放
function zoomIn() {
  scale.value = Math.min(scale.value * 1.2, 3.0)
  renderPage(currentPage.value)
}

function zoomOut() {
  scale.value = Math.max(scale.value / 1.2, 0.5)
  renderPage(currentPage.value)
}

function fitWidth() {
  if (!containerRef.value || !pdfDoc.value) return
  // 计算适应宽度的缩放比例
  // ...
}

// 监听 URL 变化
watch(() => props.pdfUrl, (url) => {
  if (url) loadPdf(url)
})

// 监听高亮请求
watch(() => props.highlightBbox, (hl) => {
  if (hl) goToPage(hl.page, hl.bbox)
})

// 暴露方法给父组件
defineExpose({ goToPage })
</script>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-deep);
}

.pdf-container {
  flex: 1;
  overflow: auto;
  position: relative;
  display: flex;
  justify-content: center;
  padding: 20px;
}

.pdf-canvas {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.highlight-layer {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.highlight-box {
  position: absolute;
  background: rgba(255, 213, 79, 0.3);
  border: 2px solid rgba(255, 213, 79, 0.8);
  border-radius: 2px;
  transition: opacity 0.5s;
}

.highlight-box.active {
  animation: highlightPulse 0.5s ease-out;
}

@keyframes highlightPulse {
  0% { transform: scale(1.1); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.pdf-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
}

.placeholder-icon {
  font-size: 64px;
  opacity: 0.3;
  margin-bottom: 16px;
}
</style>
```

### 可拖拽分隔面板

```vue
<!-- components/layout/SplitPane.vue -->
<template>
  <div class="split-pane" :class="{ vertical: direction === 'vertical' }">
    <div 
      class="pane pane-left"
      :style="{ [sizeProperty]: `${leftSize}px` }"
      v-show="!leftCollapsed"
    >
      <slot name="left" />
    </div>
    
    <div 
      class="resizer"
      @mousedown="startResize"
      v-show="!leftCollapsed && !rightCollapsed"
    >
      <div class="resizer-handle" />
    </div>
    
    <div class="pane pane-right" :style="{ flex: 1 }">
      <slot name="right" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(defineProps<{
  direction?: 'horizontal' | 'vertical'
  defaultSize?: number
  minSize?: number
  maxSize?: number
  leftCollapsed?: boolean
  rightCollapsed?: boolean
}>(), {
  direction: 'horizontal',
  defaultSize: 280,
  minSize: 200,
  maxSize: 600,
  leftCollapsed: false,
  rightCollapsed: false
})

const leftSize = ref(props.defaultSize)
const isResizing = ref(false)

const sizeProperty = computed(() => 
  props.direction === 'horizontal' ? 'width' : 'height'
)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startPos = props.direction === 'horizontal' ? e.clientX : e.clientY
  const startSize = leftSize.value
  
  const onMouseMove = (e: MouseEvent) => {
    const currentPos = props.direction === 'horizontal' ? e.clientX : e.clientY
    const delta = currentPos - startPos
    leftSize.value = Math.min(
      Math.max(startSize + delta, props.minSize),
      props.maxSize
    )
  }
  
  const onMouseUp = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
.split-pane {
  display: flex;
  height: 100%;
  width: 100%;
}

.split-pane.vertical {
  flex-direction: column;
}

.pane {
  overflow: hidden;
}

.resizer {
  flex-shrink: 0;
  width: 4px;
  background: var(--border-color);
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.resizer:hover {
  background: var(--accent-blue);
}

.vertical .resizer {
  width: 100%;
  height: 4px;
  cursor: row-resize;
}

.resizer-handle {
  width: 2px;
  height: 30px;
  background: var(--text-muted);
  border-radius: 1px;
  opacity: 0;
  transition: opacity 0.2s;
}

.resizer:hover .resizer-handle {
  opacity: 1;
}
</style>
```

---

## 📐 新布局设计

### 四栏可调布局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  OpenIndex                                      🔍 搜索    🌙/☀️    设置 ⚙️  │
├────────────┬───────────────────────┬────────────────────┬───────────────────┤
│  文档库    │    PDF 预览           │    AI 对话         │   引用/结构       │
│  ─────     │                       │                    │                   │
│  📁+ 新建  │  ┌─────────────────┐  │  ┌──────────────┐  │   [文本块] [结构] │
│            │  │                 │  │  │ 用户: ...    │  │                   │
│  📁 机器   │  │                 │  │  └──────────────┘  │   ┌─────────────┐ │
│    📑 论文1│  │    PDF 内容     │  │  ┌──────────────┐  │   │ Page 3      │ │
│    📑 论文2│  │                 │  │  │ AI: ...      │  │   │ 引用内容... │ │
│            │  │   (可缩放)      │  │  │ [P3] [P5]    │  │   └─────────────┘ │
│  📂 未分类 │  │                 │  │  └──────────────┘  │                   │
│    📑 新论文│  └─────────────────┘  │                    │                   │
│            │                       │  ┌──────────────┐  │                   │
│  ─────     │  [<] 第 3/12 页 [>]   │  │ 输入问题... │  │                   │
│  + 上传    │  [🔍] [📐] [📥]       │  └──────────────┘  │                   │
├────────────┴───────────────────────┴────────────────────┴───────────────────┤
│  状态栏: 文档 xxx.pdf | 12 页 | 已解析 | 节点: 45                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 可拖拽分隔条

```
│ 左侧 │◀═══▶│ 中左 │◀═══▶│ 中右 │◀═══▶│ 右侧 │
      ↑           ↑           ↑
   可拖拽      可拖拽      可拖拽
```

### 布局模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| **四栏** | 库 + PDF + 对话 + 引用 | 大屏桌面 |
| **三栏** | 隐藏库，PDF + 对话 + 引用 | 中等屏幕 |
| **双栏** | PDF + 对话（引用折叠） | 专注阅读 |
| **聚焦** | 仅对话（全屏） | 纯问答模式 |

快捷键支持：
- `Cmd/Ctrl + 1` - 切换库面板
- `Cmd/Ctrl + 2` - 切换 PDF 面板
- `Cmd/Ctrl + 3` - 切换引用面板

---

## 🎨 UI/UX 增强

### 1. 视觉优化

#### 1.1 渐变背景增强
```css
.app-container {
    background: 
        radial-gradient(ellipse at top left, rgba(34, 211, 238, 0.03) 0%, transparent 50%),
        radial-gradient(ellipse at bottom right, rgba(167, 139, 250, 0.03) 0%, transparent 50%),
        var(--bg-deep);
}
```

#### 1.2 玻璃拟态效果
```css
.panel-header {
    background: rgba(22, 26, 34, 0.8);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}
```

#### 1.3 阴影层次
```css
.card {
    box-shadow: 
        0 1px 2px rgba(0,0,0,0.1),
        0 4px 8px rgba(0,0,0,0.1),
        0 8px 16px rgba(0,0,0,0.1);
}
```

### 2. 动效增强

#### 2.1 面板展开动画
```css
.panel {
    transition: 
        width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
        opacity 0.2s ease;
}
```

#### 2.2 消息出现动画
```css
@keyframes messageSlideIn {
    from {
        opacity: 0;
        transform: translateY(20px) scale(0.95);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

.message {
    animation: messageSlideIn 0.3s ease-out;
}
```

#### 2.3 加载骨架屏
```css
.skeleton {
    background: linear-gradient(
        90deg,
        var(--bg-tertiary) 0%,
        var(--bg-hover) 50%,
        var(--bg-tertiary) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

### 3. Toast 通知系统

```javascript
// 显示 Toast
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${getToastIcon(type)}</span>
        <span class="toast-message">${message}</span>
    `;
    document.getElementById('toast-container').appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// 使用
showToast('文档上传成功', 'success');
showToast('删除失败：网络错误', 'error');
showToast('正在解析文档...', 'loading');
```

---

## 📄 PDF 查看器集成

### 1. PDF.js 集成方案

#### 1.1 引入 PDF.js

```html
<!-- 在 head 中引入 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script>
    pdfjsLib.GlobalWorkerOptions.workerSrc = 
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
</script>
```

#### 1.2 PDF 查看器组件结构

```html
<div class="pdf-panel">
    <!-- 工具栏 -->
    <div class="pdf-toolbar">
        <div class="pdf-toolbar-left">
            <button id="pdf-prev" title="上一页">◀</button>
            <span id="pdf-page-info">第 1/10 页</span>
            <button id="pdf-next" title="下一页">▶</button>
        </div>
        <div class="pdf-toolbar-center">
            <input type="text" id="pdf-search" placeholder="搜索文档...">
        </div>
        <div class="pdf-toolbar-right">
            <button id="pdf-zoom-out" title="缩小">−</button>
            <span id="pdf-zoom-level">100%</span>
            <button id="pdf-zoom-in" title="放大">+</button>
            <button id="pdf-fit-width" title="适应宽度">⇔</button>
            <button id="pdf-download" title="下载">📥</button>
        </div>
    </div>
    
    <!-- PDF 内容区 -->
    <div class="pdf-container" id="pdf-container">
        <canvas id="pdf-canvas"></canvas>
        <!-- 高亮层 -->
        <div class="pdf-highlight-layer" id="pdf-highlight-layer"></div>
        <!-- 文本层（用于选择） -->
        <div class="pdf-text-layer" id="pdf-text-layer"></div>
    </div>
    
    <!-- 缩略图侧边栏（可选） -->
    <div class="pdf-thumbnails" id="pdf-thumbnails"></div>
</div>
```

#### 1.3 PDF 查看器核心类

```javascript
class PDFViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = document.getElementById('pdf-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.pdfDoc = null;
        this.currentPage = 1;
        this.scale = 1.0;
        this.highlights = [];
    }

    async load(url) {
        this.pdfDoc = await pdfjsLib.getDocument(url).promise;
        this.totalPages = this.pdfDoc.numPages;
        await this.renderPage(1);
        this.updatePageInfo();
    }

    async renderPage(pageNum) {
        const page = await this.pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale: this.scale });
        
        this.canvas.width = viewport.width;
        this.canvas.height = viewport.height;
        
        await page.render({
            canvasContext: this.ctx,
            viewport: viewport
        }).promise;
        
        this.currentPage = pageNum;
        this.renderHighlights();
    }

    // 跳转到指定页面并高亮区域
    async goToPage(pageNum, bbox = null) {
        await this.renderPage(pageNum);
        if (bbox) {
            this.highlightArea(bbox);
        }
    }

    // 高亮指定区域
    highlightArea(bbox, color = 'rgba(255, 213, 79, 0.3)') {
        const layer = document.getElementById('pdf-highlight-layer');
        const highlight = document.createElement('div');
        highlight.className = 'pdf-highlight';
        highlight.style.cssText = `
            position: absolute;
            left: ${bbox[0] * this.scale}px;
            top: ${bbox[1] * this.scale}px;
            width: ${(bbox[2] - bbox[0]) * this.scale}px;
            height: ${(bbox[3] - bbox[1]) * this.scale}px;
            background: ${color};
            border: 2px solid rgba(255, 213, 79, 0.8);
            border-radius: 2px;
            pointer-events: none;
            animation: highlightPulse 2s ease-out;
        `;
        layer.appendChild(highlight);
        
        // 3 秒后淡出
        setTimeout(() => {
            highlight.style.transition = 'opacity 0.5s';
            highlight.style.opacity = '0';
            setTimeout(() => highlight.remove(), 500);
        }, 3000);
    }

    zoomIn() {
        this.scale = Math.min(this.scale * 1.2, 3.0);
        this.renderPage(this.currentPage);
    }

    zoomOut() {
        this.scale = Math.max(this.scale / 1.2, 0.5);
        this.renderPage(this.currentPage);
    }

    fitWidth() {
        // 根据容器宽度自动计算缩放
        // ...
    }
}
```

### 2. 引用点击跳转

```javascript
// 点击引用块时跳转到 PDF 对应位置
function onReferenceClick(ref) {
    if (!pdfViewer || !ref.page_num) return;
    
    // 跳转到页面
    pdfViewer.goToPage(ref.page_num, ref.bbox);
    
    // 滚动到视图中心
    const container = document.getElementById('pdf-container');
    if (ref.bbox) {
        const scrollY = ref.bbox[1] * pdfViewer.scale - container.clientHeight / 2;
        container.scrollTo({ top: scrollY, behavior: 'smooth' });
    }
}
```

### 3. 双向联动

```
┌─────────────────────────────────────────────────────────────────┐
│                        双向联动流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  对话区引用                    PDF 查看器                        │
│  ┌─────────────┐              ┌─────────────┐                   │
│  │ [P3] 引用   │──点击──────▶│ 跳转第 3 页  │                   │
│  │ 文本块...   │              │ 高亮 bbox   │                   │
│  └─────────────┘              └─────────────┘                   │
│                                                                 │
│  ┌─────────────┐              ┌─────────────┐                   │
│  │ 新增引用   │◀──选中文本───│ 用户选择    │                   │
│  │ 添加到对话 │              │ PDF 中文本  │                   │
│  └─────────────┘              └─────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 React 备选方案

如果你更熟悉 React，这里是 React 版本的架构：

### 项目结构 (React)

```
md2tree/openindex/frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── SplitPane.tsx
│   │   ├── pdf/
│   │   │   ├── PdfViewer.tsx
│   │   │   └── PdfToolbar.tsx
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx
│   │   │   └── MessageList.tsx
│   │   └── common/
│   │       └── Modal.tsx
│   ├── hooks/
│   │   ├── useApi.ts
│   │   ├── usePdf.ts
│   │   └── useToast.ts
│   ├── stores/
│   │   └── useStore.ts      # Zustand store
│   └── types/
│       └── index.ts
```

### React 状态管理 (Zustand)

```typescript
// stores/useStore.ts
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface AppState {
  // 文档
  libraries: Library[]
  documents: Document[]
  currentDoc: Document | null
  
  // 对话
  messages: Message[]
  isLoading: boolean
  
  // UI
  sidebarVisible: boolean
  pdfPanelVisible: boolean
  
  // Actions
  setCurrentDoc: (doc: Document | null) => void
  addMessage: (msg: Message) => void
  toggleSidebar: () => void
}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        libraries: [],
        documents: [],
        currentDoc: null,
        messages: [],
        isLoading: false,
        sidebarVisible: true,
        pdfPanelVisible: true,
        
        setCurrentDoc: (doc) => set({ currentDoc: doc }),
        addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
        toggleSidebar: () => set((s) => ({ sidebarVisible: !s.sidebarVisible }))
      }),
      { name: 'openindex-storage' }
    )
  )
)
```

### React PDF 查看器组件

```tsx
// components/pdf/PdfViewer.tsx
import { useEffect, useRef, useState, useCallback } from 'react'
import * as pdfjsLib from 'pdfjs-dist'

interface Props {
  pdfUrl: string | null
  highlightBbox?: { page: number; bbox: number[] } | null
  onPageChange?: (page: number) => void
}

export function PdfViewer({ pdfUrl, highlightBbox, onPageChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [scale, setScale] = useState(1.0)
  const [highlights, setHighlights] = useState<Array<{ bbox: number[] }>>([])

  // 加载 PDF
  useEffect(() => {
    if (!pdfUrl) return
    
    pdfjsLib.getDocument(pdfUrl).promise.then(doc => {
      setPdfDoc(doc)
      renderPage(doc, 1)
    })
  }, [pdfUrl])

  // 渲染页面
  const renderPage = useCallback(async (doc: pdfjsLib.PDFDocumentProxy, pageNum: number) => {
    const page = await doc.getPage(pageNum)
    const viewport = page.getViewport({ scale })
    const canvas = canvasRef.current!
    const ctx = canvas.getContext('2d')!
    
    canvas.width = viewport.width
    canvas.height = viewport.height
    
    await page.render({ canvasContext: ctx, viewport }).promise
    setCurrentPage(pageNum)
    onPageChange?.(pageNum)
  }, [scale, onPageChange])

  // 监听高亮请求
  useEffect(() => {
    if (highlightBbox && pdfDoc) {
      renderPage(pdfDoc, highlightBbox.page)
      setHighlights([{ bbox: highlightBbox.bbox }])
      
      const timer = setTimeout(() => setHighlights([]), 3000)
      return () => clearTimeout(timer)
    }
  }, [highlightBbox, pdfDoc, renderPage])

  if (!pdfUrl) {
    return (
      <div className="pdf-placeholder">
        <span className="icon">📄</span>
        <p>选择文档查看 PDF</p>
      </div>
    )
  }

  return (
    <div className="pdf-viewer">
      <div className="pdf-toolbar">
        <button onClick={() => pdfDoc && renderPage(pdfDoc, currentPage - 1)}>◀</button>
        <span>{currentPage} / {pdfDoc?.numPages || 0}</span>
        <button onClick={() => pdfDoc && renderPage(pdfDoc, currentPage + 1)}>▶</button>
        <button onClick={() => setScale(s => Math.min(s * 1.2, 3))}>+</button>
        <button onClick={() => setScale(s => Math.max(s / 1.2, 0.5))}>−</button>
      </div>
      
      <div className="pdf-container">
        <canvas ref={canvasRef} />
        {highlights.map((hl, i) => (
          <div
            key={i}
            className="highlight-box"
            style={{
              left: hl.bbox[0] * scale,
              top: hl.bbox[1] * scale,
              width: (hl.bbox[2] - hl.bbox[0]) * scale,
              height: (hl.bbox[3] - hl.bbox[1]) * scale
            }}
          />
        ))}
      </div>
    </div>
  )
}
```

---

## 📅 实施计划（Vue 3 版本）

### Phase 0: 项目初始化（0.5 天）

```bash
# 创建 Vue 3 项目
cd md2tree/openindex
npm create vite@latest frontend -- --template vue-ts

cd frontend
npm install
npm install pinia @vueuse/core pdfjs-dist
npm install -D sass
```

### Phase 1: 基础架构搭建（2 天）

| 任务 | 工时 | 优先级 |
|------|------|--------|
| 1.1 设置 Pinia 状态管理 | 0.5 天 | P0 |
| 1.2 实现 API composable | 0.5 天 | P0 |
| 1.3 创建基础布局组件 | 0.5 天 | P0 |
| 1.4 配置 Vite 代理和构建 | 0.5 天 | P0 |

### Phase 2: 核心组件开发（4-5 天）

| 任务 | 工时 | 优先级 |
|------|------|--------|
| 2.1 Sidebar 组件（库管理） | 1 天 | P0 |
| 2.2 PdfViewer 组件 | 1.5 天 | P0 |
| 2.3 ChatPanel 组件 | 1 天 | P0 |
| 2.4 ReferencePanel 组件 | 0.5 天 | P0 |
| 2.5 SplitPane 可拖拽分隔 | 0.5 天 | P1 |

### Phase 3: 功能完善（2-3 天）

| 任务 | 工时 | 优先级 |
|------|------|--------|
| 3.1 PDF 高亮和跳转联动 | 0.5 天 | P0 |
| 3.2 文档上传和拖拽 | 0.5 天 | P1 |
| 3.3 对话历史管理 | 0.5 天 | P1 |
| 3.4 快捷键支持 | 0.5 天 | P2 |
| 3.5 布局状态持久化 | 0.5 天 | P2 |

### Phase 4: UI/UX 打磨（2 天）

| 任务 | 工时 | 优先级 |
|------|------|--------|
| 4.1 Toast 通知组件 | 0.5 天 | P1 |
| 4.2 加载骨架屏 | 0.5 天 | P1 |
| 4.3 过渡动画优化 | 0.5 天 | P2 |
| 4.4 深色主题完善 | 0.5 天 | P2 |

### Phase 5: 集成和部署（1 天）

| 任务 | 工时 | 优先级 |
|------|------|--------|
| 5.1 配置生产构建 | 0.5 天 | P0 |
| 5.2 FastAPI 静态文件托管 | 0.5 天 | P0 |

**总计**: 11-13 天

---

## 🚀 快速启动命令

### 开发模式

```bash
# 终端 1: 启动后端
cd /home/lz/repo/PageIndex
source .venv/bin/activate
python -m md2tree.openindex.app

# 终端 2: 启动前端开发服务器
cd /home/lz/repo/PageIndex/md2tree/openindex/frontend
npm run dev
```

### 生产构建

```bash
# 构建前端
cd frontend
npm run build

# 构建产物会输出到 ../static/
# FastAPI 会自动托管这些静态文件
```

### Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8090',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: '../static',
    emptyOutDir: true
  }
})
```

---

## ✅ 验收标准

### 基础功能
- [ ] Vue 3 项目正常运行，无控制台错误
- [ ] 所有现有功能正常工作（上传、删除、库管理）
- [ ] API 调用正常，状态管理正确

### PDF 查看器
- [ ] 选择文档后自动加载 PDF 预览
- [ ] 支持翻页、缩放、适应宽度
- [ ] 点击引用可跳转到 PDF 对应位置并高亮
- [ ] 高亮区域 3 秒后自动淡出

### 布局系统
- [ ] 四栏布局正常显示
- [ ] 可拖拽调节各面板宽度
- [ ] 可折叠/展开各面板
- [ ] 布局状态保存到 localStorage

### 用户体验
- [ ] 操作成功/失败有 Toast 提示
- [ ] 加载时显示骨架屏而非空白
- [ ] 过渡动画流畅自然
- [ ] 快捷键可用

### 代码质量
- [ ] TypeScript 类型完整
- [ ] 组件职责单一，可复用
- [ ] 无 ESLint 警告

---

## 📊 Vue vs React 选择建议

| 考量因素 | 选 Vue 3 | 选 React |
|---------|---------|----------|
| 团队熟悉度 | 团队更熟悉 Vue | 团队更熟悉 React |
| 学习曲线 | 稍平缓，模板更直观 | Hooks 需要适应 |
| 生态系统 | Element Plus, Naive UI | Ant Design, MUI |
| 中文资源 | 非常丰富 | 丰富 |
| TypeScript | Volar 支持好 | 原生支持更好 |
| 性能 | 两者相当 | 两者相当 |
| 包体积 | 稍小 | 稍大 |

**我的建议**: 如果没有强烈偏好，**推荐 Vue 3**，因为：
1. 单文件组件 (SFC) 更直观
2. Composition API 和 React Hooks 类似，但更灵活
3. 中文文档和社区更活跃
4. Pinia 比 Redux 简洁很多

---

## 🔗 参考资源

### Vue 3
- [Vue 3 官方文档](https://cn.vuejs.org/)
- [Pinia 文档](https://pinia.vuejs.org/zh/)
- [VueUse 工具库](https://vueuse.org/)
- [Naive UI 组件库](https://www.naiveui.com/)

### React
- [React 官方文档](https://react.dev/)
- [Zustand 状态管理](https://zustand-demo.pmnd.rs/)
- [TanStack Query](https://tanstack.com/query/latest)

### 通用
- [PDF.js 文档](https://mozilla.github.io/pdf.js/)
- [Vite 文档](https://cn.vitejs.dev/)

---

## 💡 下一步行动

1. **确认框架选择**: Vue 3 还是 React?
2. **开始 Phase 0**: 初始化项目
3. **按计划推进**: 每个 Phase 完成后进行验收

---

*计划创建时间: 2026-01-12*  
*更新时间: 2026-01-12 - 添加 Vue 3/React 方案*
