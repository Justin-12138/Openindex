# 修复文档隔离问题

> 修复时间: 2026-01-12

## 问题描述

不同的 PDF 应该有不同的对话历史，以及对应的 PDF 标注坐标。但现在是一个对话所有的 PDF 都有对应的标记。

## 问题原因

1. **前端状态未隔离**：切换文档时，`chatStore` 中的 `locations`、`references`、`selectedNodes` 等状态没有被清空
2. **PDF 高亮未过滤**：PDF 查看器监听 `chatStore.locations` 时，没有检查这些标注是否属于当前文档
3. **对话加载时机**：切换文档时，没有自动加载新文档的对话列表

## 修复方案

### 1. 添加 `clearForDocument()` 方法

在 `chatStore` 中添加新方法，用于清空与当前文档相关的状态：

```typescript
function clearForDocument() {
  // 只清空与当前文档相关的状态，保留对话列表
  messages.value = []
  references.value = []
  selectedNodes.value = []
  locations.value = []
}
```

### 2. 文档切换时清空状态

在 `documentStore.selectDocument()` 中，切换文档时调用 `clearForDocument()`：

```typescript
async function selectDocument(doc: Document) {
  // 切换文档时，清空之前文档的聊天状态
  const chatStore = useChatStore()
  chatStore.clearForDocument()
  
  currentDoc.value = doc
  // ... 其他逻辑
  
  // 加载新文档的对话列表
  await chatStore.loadConversations(doc.id)
}
```

### 3. 加载对话时清空状态

在 `loadConversations()` 开始时清空状态，确保不会显示其他文档的对话：

```typescript
async function loadConversations(docId: string) {
  // 先清空当前状态
  clearForDocument()
  
  conversations.value = await api.conversations.list(docId)
  // ... 其他逻辑
}
```

### 4. 从消息中恢复标注信息

在 `loadConversation()` 中，从消息中提取标注信息，确保只显示当前对话的标注：

```typescript
async function loadConversation(convId: string) {
  const conv = await api.conversations.get(convId)
  // ... 加载消息
  
  // 从最新的 assistant 消息中提取标注信息
  const assistantMessages = messages.value
    .filter(msg => msg.role === 'assistant')
    .reverse()
  
  if (assistantMessages.length > 0) {
    const latestMessage = assistantMessages[0]
    if (latestMessage.locations) {
      locations.value = latestMessage.locations
    }
    // ... 其他标注信息
  }
}
```

### 5. PDF 高亮过滤

在 `PdfViewer.vue` 中，监听文档切换，清空高亮：

```typescript
// 监听文档切换，清空高亮
watch(() => docStore.pdfUrl, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl) {
    highlightBoxes.value = []
  }
})
```

## 修复文件

1. `md2tree/openindex/frontend/src/stores/chat.ts`
   - 添加 `clearForDocument()` 方法
   - 修改 `loadConversations()` 在开始时清空状态
   - 修改 `loadConversation()` 从消息中恢复标注信息

2. `md2tree/openindex/frontend/src/stores/document.ts`
   - 修改 `selectDocument()` 切换文档时清空聊天状态并加载新文档的对话

3. `md2tree/openindex/frontend/src/components/pdf/PdfViewer.vue`
   - 添加文档切换监听，清空高亮

## 测试建议

1. 上传两个不同的 PDF 文档
2. 在第一个文档中创建对话并查询，查看 PDF 标注
3. 切换到第二个文档
4. 验证：
   - 第一个文档的标注不应该显示在第二个文档上
   - 第二个文档应该显示自己的对话列表
   - 在第二个文档中查询时，只显示第二个文档的标注

---

*修复完成时间: 2026-01-12*
