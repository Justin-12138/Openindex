# 个人论文管理系统 - 开发文档

## 项目概述

基于 md2tree 构建的个人论文管理应用，核心功能是将 PDF 论文转换为结构化的 Markdown 树，并实现智能检索和引用定位。

## 核心问题分析

### 问题 1: PDF 到 Markdown 的准确解析

#### 现状分析

当前 PDF 解析面临的主要挑战：

| 挑战 | 描述 | 影响 |
|------|------|------|
| **双栏布局** | 学术论文通常采用双栏排版 | 解析后文本顺序混乱 |
| **公式/表格** | 数学公式和表格结构复杂 | 容易解析错误或丢失 |
| **图片/图表** | 图表说明与图片分离 | 上下文关联丢失 |
| **OCR 扫描件** | 扫描的 PDF 需要文字识别 | 识别率影响准确性 |
| **特殊字符** | 上标、下标、特殊符号 | 转换后语义丢失 |

#### 现有工具对比

##### 1. MinerU [推荐]

**特点**：
- 一站式 PDF 文档解析工具
- 支持在线 API + 离线部署 + 桌面客户端
- 输出格式包含 `page_idx` 和 `bbox` 信息
- 对表格、公式、图片有专门处理

**优势**：
- ⭐ **内置页码映射** (`page_idx` 字段)
- ⭐ **内置位置映射** (`bbox` 字段)
- 开源，可本地部署
- 支持中英文

**GitHub**: [opendatalab/MinerU](https://github.com/opendatalab/MinerU)

**输出格式示例**：
```json
{
  "layout_dets": [
    {
      "category_id": 1,
      "bbox": [x1, y1, x2, y2],
      "text": "content",
      "page_idx": 0,
      "type": "text"
    }
  ]
}
```

##### 2. Marker

**特点**：
- 将 PDF 转换为 Markdown + JSON
- 支持多种文档格式 (PDF, DOCX, PPTX, XLSX, HTML, EPUB)
- 速度快、准确性高

**GitHub**: [datalab-to/marker](https://github.com/datalab-to/marker)

##### 3. PyMuPDF4LLM

**特点**：
- 专门为 LLM/RAG 应用设计
- 数字 PDF 效果较好
- 转换结果可能较分散

##### 4. pdfplumber

**特点**：
- 布局感知能力强
- 适合数字 PDF
- 数据提取工具

##### 5. 其他工具

- **MarkItDown** (Microsoft): 支持页/行/词级别的 bounding box (2025年8月新增)
- **Unstructured**: 提供多种解析策略

#### 推荐方案

```
优先级 1: MinerU (内置 page_idx 和 bbox)
优先级 2: Marker (JSON 输出格式规范)
优先级 3: PyMuPDF4LLM + 自定义页码追踪
```

---

### 问题 2: 解析内容与 PDF 页码对齐

#### 技术挑战

```
PDF 文档
├── 物理页码 (PDF 内部页码)
├── 显示页码 (页眉/页脚显示的页码)
├── 逻辑页码 (章节/文章的页码)
└── 解析后的 Markdown 行号
```

这四种页码系统需要统一映射。

#### 解决方案

##### 方案 A: 使用 MinerU 的原生支持 [推荐]

**MinerU 直接提供页码映射**：

```json
{
  "layout_dets": [
    {
      "page_idx": 0,           // PDF 物理页码 (从 0 开始)
      "bbox": [50, 100, 500, 150],  // 位置坐标 [x1, y1, x2, y2]
      "text": "这是第一段文字",
      "type": "text"
    }
  ]
}
```

**实现步骤**：

1. 使用 MinerU 解析 PDF
2. 在树结构中添加 `page_idx` 和 `bbox` 字段
3. 通过 `page_idx` 直接定位到 PDF 页

**代码示例**：

```python
# 使用 MinerU 解析
from mineru import SingleFileDocument

doc = SingleFileDocument(pdf_path)
result = doc.parse()

# 构建带页码信息的树
def build_tree_with_page_info(content_blocks):
    for block in content_blocks:
        node = {
            'text': block['text'],
            'page_idx': block['page_idx'],  # 页码
            'bbox': block['bbox'],           # 位置
            'title': extract_title(block),    # 标题
        }
        # ... 构建树
```

**引用定位**：

```markdown
> 根据 MinerU 的输出格式，每个内容块都包含 `page_idx` 字段（PDF 物理页码，从 0 开始）和 `bbox` 字段（边界框坐标 [x1, y1, x2, y2]），可以直接映射回原始 PDF 文件。

来源: [MinerU - Output File Format](https://opendatalab.github.io/MinerU/reference/output_files/)
```

##### 方案 B: MarkItDown + Bounding Box (Microsoft, 2025年8月新增)

**Microsoft MarkItDown** 在 2025年8月添加了可选的页/行/词级 bounding box 支持。

**特点**：
- PDF 提取支持页锚定的 bounding box
- 光学字符识别 (OCR) 支持字符级 bounding box
- 位置精度高

**来源**: [microsoft/markitdown PR #1398](https://github.com/microsoft/markitdown/pull/1398)

##### 方案 C: PyMuPDF 自定义追踪

如果使用其他工具，需要自己实现页码追踪：

```python
import fitz  # PyMuPDF

def parse_pdf_with_page_tracking(pdf_path):
    doc = fitz.open(pdf_path)
    page_content_map = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" in block:  # 文本块
                for line in block["lines"]:
                    for span in line["spans"]:
                        page_content_map.append({
                            "text": span["text"],
                            "page_num": page_num,
                            "bbox": span["bbox"],  # [x0, y0, x1, y1]
                            "font": span["font"],
                            "size": span["size"],
                        })

    return page_content_map
```

##### 方案 D: 混合方案 (Markdown 注入法)

在 Markdown 中注入页码标记：

```markdown
<!-- PAGE 1 -->

# Introduction

This is the introduction...

<!-- PAGE 2 -->

## Background

More content...
```

**优点**：
- 简单直接
- 可读性好

**缺点**：
- 增加 Markdown 冗余
- 需要解析时处理标记

---

## 技术方案设计

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     PDF 论文管理应用                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  PDF 输入   │───▶│   解析模块   │───▶│   树构建     │  │
│  └─────────────┘    └──────────────┘    │              │  │
│                           │            │  带页码映射   │  │
│                           ▼            └──────────────┘  │
│  ┌─────────────┐    ┌──────────────┐                     │
│  │ MinerU API │    │   Marker     │                     │
│  │ (推荐)      │    │   (备选)     │                     │
│  └─────────────┘    └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### 数据结构设计

#### 增强的树节点结构

```python
class PaperNode:
    """论文树节点，包含页码映射信息"""
    def __init__(self):
        self.node_id: str          # 节点 ID
        self.title: str            # 标题
        self.text: str             # 文本内容
        self.summary: str          # 摘要 (可选)
        self.page_range: Tuple[int, int] = (None, None)  # [起始页, 结束页]
        self.bboxes: List[List[float]] = []  # 每段的边界框
        self.node_type: str = "section"  # section/subsection/paragraph
        self.nodes: List['PaperNode'] = []
```

#### 检索结果格式

```python
class SearchResult:
    """检索结果，包含可定位引用"""
    query: str                    # 查询
    answer: str                   # 生成的答案
    sources: List[SourceCitation] # 引用来源

class SourceCitation:
    """可定位的引用"""
    node_id: str                  # 节点 ID
    title: str                    # 标题
    page_num: int                 # PDF 页码
    bbox: List[float]             # 位置坐标
    text_snippet: str             # 引用文本片段
    pdf_link: str                 # PDF + 页码的链接 (如 file.pdf#page=5)
```

### 引用定位格式

#### Markdown 中的引用

```markdown
根据研究，内存墙问题的成因包括：

> 内存带宽的增长速度远低于计算能力的增长速度。
> 来源: [AI and Memory Wall, p.2, (50, 120, 500, 150)](#pdf-page=2)

过去 20 年的具体数据如下：

> FLOPS 增长了 60,000 倍，DRAM 带宽仅增长 100 倍。
> 来源: [I. INTRODUCTION, p.3](#pdf-page=3)
```

#### PDF 链接格式

```html
<!-- 使用 hash 定位 -->
<a href="paper.pdf#page=5">查看 PDF 第 5 页</a>

<!-- 使用坐标定位 (如果 PDF viewer 支持) -->
<a href="paper.pdf#page=5&bbox=50,100,500,150">查看具体段落</a>
```

---

## 实现路线图

### Phase 1: 基础解析 (Week 1)

- [ ] 集成 MinerU API
- [ ] 实现 PDF → Markdown + JSON 转换
- [ ] 保存 `page_idx` 和 `bbox` 信息
- [ ] 基础树结构构建

### Phase 2: 页码映射 (Week 2)

- [ ] 在树节点中添加 `page_range` 字段
- [ ] 实现 `create_page_mapping()` 函数
- [ ] 测试页码映射准确性

### Phase 3: 检索增强 (Week 3)

- [ ] 集成现有的 RAG pipeline
- [ ] 实现带引用定位的检索
- [ ] 生成答案时包含页码引用

### Phase 4: 用户界面 (Week 4)

- [ ] PDF 预览 + 高亮定位
- [ ] 检索结果展示
- [ ] 引用跳转功能

---

## 关键代码模块

### 1. PDF 解析模块

```python
# paper_parser.py

from mineru import SingleFileDocument
import json

class PaperParser:
    def __init__(self):
        self.doc = None

    def parse_pdf(self, pdf_path: str) -> dict:
        """解析 PDF，返回带页码信息的内容"""
        doc = SingleFileDocument(pdf_path)
        result = doc.parse()

        # 提取内容块，每个块包含页码和位置信息
        content_blocks = []
        for item in result['layout_dets']:
            content_blocks.append({
                'text': item['text'],
                'page_idx': item['page_idx'],
                'bbox': item['bbox'],
                'type': item.get('type', 'text'),
            })

        return {
            'doc_name': Path(pdf_path).stem,
            'total_pages': len(result['pdf_info']),
            'content_blocks': content_blocks,
        }
```

### 2. 页码映射模块

```python
# page_mapper.py

def create_page_mapping(tree: List[dict]) -> Dict[str, dict]:
    """创建节点 ID 到页码的映射"""
    page_map = {}

    def traverse(nodes):
        for node in nodes:
            node_id = node.get('node_id')
            if node_id:
                # 收集该节点涉及的所有页码
                pages = extract_pages_from_node(node)
                page_map[node_id] = {
                    'page_range': (min(pages), max(pages)) if pages else None,
                    'bboxes': node.get('bboxes', []),
                }

            if 'nodes' in node:
                traverse(node['nodes'])

    traverse(tree)
    return page_map

def extract_pages_from_node(node: dict) -> Set[int]:
    """从节点的所有文本中提取页码"""
    pages = set()

    # 从 node 的 line_num 中提取页码
    # (需要解析时保存每行的页码信息)
    for line_info in node.get('line_infos', []):
        pages.add(line_info['page_idx'])

    return pages
```

### 3. 引用生成模块

```python
# citation.py

def format_citation(source: dict, pdf_name: str) -> str:
    """格式化引用"""
    title = source.get('title', 'Unknown')
    page_num = source.get('page_num', 0)
    bbox = source.get('bbox', [])

    # Markdown 链接格式
    link = f"{pdf_name}.pdf#page={page_num}"

    citation = f"[{title}, p.{page_num}]({link})"

    # 如果有 bbox，添加位置信息
    if bbox:
        citation += f" 📍 {bbox}"

    return citation
```

---

## 工具选择建议

### 推荐工具组合

| 功能 | 工具 | 理由 |
|------|------|------|
| **PDF 解析** | MinerU | 内置 page_idx + bbox，开源可本地部署 |
| **备选解析** | Marker | JSON 格式规范，准确性高 |
| **PDF 预览** | PDF.js | Web 端直接定位页码 |
| **本地预览** | PyMuPDF (fitz) | Python 原生，支持跳转 |
| **RAG 检索** | md2tree | 现有基础，已验证 |

### MinerU 部署

```bash
# 安装 MinerU
pip install miner-e

# 使用命令行
mineru_single input.pdf -o output_dir

# 或使用 Python API
from mineru import SingleFileDocument
doc = SingleFileDocument("input.pdf")
result = doc.parse()
```

---

## 参考资料

### 工具文档

- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [MinerU 输出格式文档](https://opendatalab.github.io/MinerU/reference/output_files/)
- [Marker GitHub](https://github.com/datalab-to/marker)
- [PyMuPDF 文档](https://pymupdf.readthedocs.io/)

### 技术文章

- [PDF to Markdown 工具深度对比 (Jimmy Song, 2025)](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/)
- [2025 年 Python PDF 解析器对比](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257)
- [PyMuPDF for RAG/LLM](https://medium.com/@pymupdf/rag-llm-and-pdf-conversion-to-markdown-text-with-pymupdf-03af00259b5d)
- [Microsoft MarkItDown Bounding Box PR](https://github.com/microsoft/markitdown/pull/1398)

### 相关项目

- [PageIndex](https://github.com/anthropics/PageIndex) - 原始项目
- [Unstructured.io](https://unstructured.io/) - 文档解析平台
