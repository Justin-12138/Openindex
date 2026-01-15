# Middle JSON 集成指南

## 概述

`middle.json` 是 MinerU 输出的最精确的数据文件，包含：
- **精确的 PDF 坐标**（直接使用 PDF 坐标系，无需转换）
- **块级别的结构**（para_blocks, discarded_blocks）
- **详细的文本片段**（spans 级别）

## 文件结构

```json
{
  "pdf_info": [
    {
      "page_size": [612, 792],      // PDF 页面尺寸
      "page_idx": 0,                 // 页码
      "para_blocks": [...],          // 解析出的段落块
      "discarded_blocks": [...]      // 被丢弃的块（页眉、页脚等）
    }
  ]
}
```

### 块结构

```json
{
  "bbox": [197, 51, 413, 77],       // 精确的 PDF 坐标
  "type": "title",                   // 类型：title, text, image 等
  "angle": 0,                        // 旋转角度
  "index": 1,                        // 块索引
  "lines": [                         // 行列表
    {
      "bbox": [197, 51, 413, 77],
      "spans": [                     // 文本片段
        {
          "bbox": [197, 51, 413, 77],
          "type": "text",
          "content": "AI and Memory Wall"
        }
      ]
    }
  ]
}
```

## 核心功能：查询到块定位

这是最重要的功能：**从用户查询定位到 PDF 中的具体块**

### 使用方法

```python
from workflow import PDFToTreeWorkflow

workflow = PDFToTreeWorkflow(
    pdf_path="data/pdfs/2403.14123v1_origin.pdf",
    mineru_output_dir="data/pdfs/res/2403.14123v1_origin",
    use_middle_json=True  # 使用 middle.json
)

# 搜索并定位到块
results = workflow.search_and_locate_blocks(
    query="memory wall",
    output_html="results/search.html",
    max_results=10
)

print(f"找到 {results['total_results']} 个结果")

for result in results['results']:
    print(f"第 {result['page_num']} 页")
    print(f"bbox: {result['bbox']}")
    print(f"上下文: {result['context']}")
    print(f"PDF 链接: {result['pdf_link']}")

workflow.close()
```

### 输出结果

```json
{
  "query": "memory wall",
  "source": "middle.json",
  "total_results": 9,
  "returned_results": 5,
  "results": [
    {
      "rank": 1,
      "page_idx": 0,
      "page_num": 1,
      "bbox": [197, 51, 413, 77],
      "type": "title",
      "context": "AI and Memory Wall...",
      "pdf_link": "data/pdfs/2403.14123v1_origin.pdf#page=1&bbox=197,51,413,77",
      "spans": [...]
    }
  ]
}
```

## 树结构与块信息集成

```python
# 运行工作流（自动使用 middle.json）
tree_data = workflow.run_basic(output_path="results/tree.json")

# 节点包含详细的块信息
node = tree_data['structure'][0]

# 标题块
title_block = node['page_info']['title_block']
# {
#   "page_idx": 0,
#   "bbox": [197, 51, 413, 77],
#   "type": "title",
#   "text": "AI and Memory Wall"
# }

# 内容块列表
content_blocks = node['page_info']['content_blocks']
# 每个块包含：page_idx, bbox, type, text, spans
```

## 直接使用 Middle JSON 解析器

```python
from middle_json_parser import MiddleJSONParser

parser = MiddleJSONParser("data/pdfs/res/2403.14123v1_origin/vlm/2403.14123v1_origin_middle.json")

# 获取所有标题
titles = parser.get_titles()
for title in titles:
    text = parser._get_block_text(title)
    print(f"[Page {title.page_idx + 1}] {text}")
    print(f"  bbox: {title.bbox}")

# 搜索文本
results = parser.search_and_locate("memory wall")

# 查找标题
title_block = parser.find_title_by_text("I. INTRODUCTION")

# 获取块的详细位置
location_info = parser.get_block_location_info(title_block)

parser.close()
```

## 坐标系统

- **坐标原点**: 左下角 (0, 0) - PDF 标准
- **坐标单位**: 点（1 点 = 1/72 英寸）
- **bbox 格式**: [x1, y1, x2, y2]
  - x1, y1: 左下角
  - x2, y2: 右上角

### 示例

```
标题 "AI and Memory Wall" 的坐标
- bbox: [197, 51, 413, 77]
- 含义：
  - 左下角: (197, 51)
  - 右上角: (413, 77)
  - 宽度: 413 - 197 = 216 点
  - 高度: 77 - 51 = 26 点
```

## 文件对比

| 文件 | 坐标精度 | 用途 |
|------|----------|------|
| `middle.json` | **精确** (PDF 坐标) | 块级定位 |
| `content_list_v2.json` | 近似 (1000x1000) | 文本提取 |
| `model.json` | 归一化 (0-1) | 模型输入 |

**推荐**: 使用 `middle.json` 进行所有需要精确坐标的操作。

## 测试

```bash
# 测试查询到块功能
python test_query_to_block.py

# 测试工作流
python workflow.py data/pdfs/2403.14123v1_origin.pdf data/pdfs/res/2403.14123v1_origin

# 直接测试 Middle JSON 解析器
python middle_json_parser.py data/pdfs/res/2403.14123v1_origin/vlm/2403.14123v1_origin_middle.json "memory wall"
```

## API 参考

### MiddleJSONParser

| 方法 | 说明 |
|------|------|
| `get_titles()` | 获取所有标题块 |
| `find_blocks_by_text(text, fuzzy)` | 查找包含文本的块 |
| `search_and_locate(query)` | 搜索并返回位置信息 |
| `get_block_location_info(block)` | 获取块的详细信息 |
| `locate_node_in_tree(title, text)` | 定位树节点在 PDF 中的位置 |

### PDFToTreeWorkflow

| 方法 | 说明 |
|------|------|
| `search_and_locate_blocks(query, output_html, max_results)` | 搜索并定位到块（核心功能） |
| `run_basic(output_path)` | 运行基础工作流 |
| `run_advanced(output_path, **kwargs)` | 运行高级工作流（带 LLM） |

## 注意事项

1. **坐标精度**: middle.json 的坐标是 PDF 坐标系，无需转换
2. **块类型**: 常见类型有 `title`, `text`, `image`, `table`
3. **被丢弃的块**: discarded_blocks 通常包含页眉、页脚、页码等
4. **性能**: middle.json 包含详细结构，解析速度较慢但结果更精确
