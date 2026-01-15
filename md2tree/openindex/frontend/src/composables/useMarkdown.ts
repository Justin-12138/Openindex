import { ref, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'

// 创建 Markdown 渲染器实例
let md: MarkdownIt | null = null

export function useMarkdown() {
  // 初始化 Markdown 渲染器
  const initMarkdown = () => {
    if (!md) {
      md = new MarkdownIt({
        html: true,
        linkify: true,
        typographer: true,
        breaks: true,
      })

      // 配置 KaTeX
      md.use(markdownItKatex, {
        throwOnError: false,
        errorColor: '#cc0000',
        displayMode: false,
      })
    }
  }

  // 渲染 Markdown 内容
  const renderMarkdown = (content: string): string => {
    if (!md) {
      initMarkdown()
    }

    if (!md) {
      return content.replace(/\n/g, '<br>')
    }

    try {
      // 渲染 Markdown
      let html = md.render(content)

      // 后处理：确保代码块正确显示
      html = html.replace(/<pre><code class="language-([^"]*)">/g, '<pre><code class="language-$1 hljs">')
      html = html.replace(/<pre><code>/g, '<pre><code class="hljs">')

      return html
    } catch (error) {
      console.warn('Markdown rendering failed:', error)
      // 失败时回退到简单文本处理
      return content.replace(/\n/g, '<br>')
    }
  }

  // 检测内容是否包含 Markdown 语法
  const hasMarkdown = (content: string): boolean => {
    const markdownPatterns = [
      /\*\*.*?\*\*/,  // 加粗
      /\*.*?\*/,      // 斜体
      /`.*?`/,        // 行内代码
      /```[\s\S]*?```/, // 代码块
      /^\s*[-*+]\s+/m, // 无序列表
      /^\s*\d+\.\s+/m, // 有序列表
      /^#{1,6}\s+/m, // 标题
      /\[.*?\]\(.*?\)/, // 链接
      /!\[.*?\]\(.*?\)/, // 图片
      /\$.*?\$/,       // 数学公式
      /\$\$.*?\$\$/,   // 块级数学公式
    ]

    return markdownPatterns.some(pattern => pattern.test(content))
  }

  // 自动检测并渲染内容
  const renderContent = (content: string): string => {
    if (hasMarkdown(content)) {
      return renderMarkdown(content)
    } else {
      // 非 Markdown 内容，保持原有逻辑
      return content.replace(/\n/g, '<br>')
    }
  }

  // 初始化
  onMounted(() => {
    initMarkdown()
  })

  return {
    renderMarkdown,
    hasMarkdown,
    renderContent,
    initMarkdown,
  }
}