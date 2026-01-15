# md2tree 架构文档

## 项目概述

md2tree 是一个将 PDF 文档转换为带有精确坐标的树结构的工具集，支持 AI 驱动的文档检索和定位功能。

## 核心流程

```
┌─────────────┐    MinerU     ┌───────────────────────────────────────┐
│    PDF      │ ──────────────►│  MinerU 输出目录                      │
│  文档       │               │  ├── *_middle.json (精确坐标)         │
└─────────────┘               │  ├── *_content_list.json              │
                              │  └── *.md (Markdown)                   │
                              └───────────────────────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
           ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
           │ MiddleJSON    │         │ md2tree.py    │         │ MinerUParser  │
           │ Parser        │         │ (Markdown→树) │         │ (备用坐标)    │
           └───────────────┘         └───────────────┘         └───────────────┘
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               │
                                               ▼
                              ┌───────────────────────────────┐
                              │     带位置信息的树结构         │
                              │  {                            │
                              │    "doc_name": "论文名",       │
                              │    "structure": [             │
                              │      {                        │
                              │        "title": "章节",       │
                              │        "node_id": "0001",     │
                              │        "text": "内容...",     │
                              │        "page_info": {         │
                              │          "page_range": [0,2], │
                              │          "title_block": {     │
                              │            "bbox": [x,y,w,h], │
                              │            "page_idx": 0      │
                              │          }                    │
                              │        }                      │
                              │      }                        │
                              │    ]                          │
                              │  }                            │
                              └───────────────────────────────┘
```

## 查询流程（核心应用）

```
用户查询
    │
    ▼
┌───────────────────────────────────────┐
│  Step 1: Query + 树结构 → LLM         │
│  让 LLM 选择最相关的 node_id          │
└───────────────────────────────────────┘
    │
    ▼  返回 node_id 列表
┌───────────────────────────────────────┐
│  Step 2: 获取对应节点的原文           │
│  从树结构中获取完整的 text 内容       │
└───────────────────────────────────────┘
    │
    ▼  node_id + 原文
┌───────────────────────────────────────┐
│  Step 3: Query + 原文 → LLM           │
│  基于原文生成答案                     │
└───────────────────────────────────────┘
    │
    ▼  答案 + 定位信息
┌───────────────────────────────────────┐
│  Step 4: 返回结果 + PDF 定位          │
│  - 答案文本                           │
│  - 来源节点信息                       │
│  - PDF 页码和 bbox 坐标               │
└───────────────────────────────────────┘
```

## 模块架构

### 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **md2tree** | `md2tree.py` | Markdown → 树结构转换 |
| **LLM** | `llm.py` | LLM API 调用封装 |
| **Summary** | `summary.py` | 节点摘要生成 |
| **Thinning** | `thinning.py` | 树剪枝算法 |
| **Utils** | `utils.py` | 工具函数 |

### 定位模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **MiddleJSONParser** | `middle_json_parser.py` | 解析 middle.json，获取精确 PDF 坐标 |
| **MinerUParser** | `mineru_parser.py` | 解析 content_list.json（备用） |
| **PDFViewer** | `pdf_viewer.py` | PDF 高亮和预览功能 |
| **Workflow** | `workflow.py` | 完整工作流整合 |

## 坐标系统

### middle.json 坐标（推荐）

middle.json 直接使用 PDF 坐标系：
- 原点在页面左下角
- 坐标单位与 PDF 点一致
- **bbox 格式**: `[x1, y1, x2, y2]`
- 无需坐标转换

```json
{
  "pdf_info": [
    {
      "page_idx": 0,
      "page_size": [612, 792],
      "para_blocks": [
        {
          "bbox": [197, 51, 413, 77],
          "type": "title",
          "lines": [
            {
              "bbox": [197, 51, 413, 77],
              "spans": [
                {
                  "bbox": [197, 51, 413, 77],
                  "type": "text",
                  "content": "AI and Memory Wall"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### content_list.json 坐标

content_list.json 使用 MinerU 内部坐标，需要转换到 PDF 坐标系。

## 数据结构

### 树节点结构

```json
{
  "title": "章节标题",
  "node_id": "0001",
  "text": "完整的章节内容...",
  "line_num": 10,
  "page_info": {
    "page_range": [0, 2],
    "title_block": {
      "page_idx": 0,
      "bbox": [197, 51, 413, 77],
      "type": "title",
      "text": "AI and Memory Wall"
    },
    "content_blocks": [
      {
        "page_idx": 0,
        "bbox": [45, 145, 301, 297],
        "type": "text",
        "text": "Abstract—The availability..."
      }
    ]
  },
  "nodes": []
}
```

### 块类型

| 类型 | 说明 |
|------|------|
| `title` | 标题 |
| `text` | 正文段落 |
| `image` | 图片 |
| `table` | 表格 |
| `interline_equation` | 行间公式 |
| `list` | 列表 |

## 配置文件

### config.toml

```toml
[llm]
api_key = ""
api_base = ""
model = "glm-4.7"
temperature = 1.0
max_concurrent_requests = 2

[mineru]
server_url = "http://101.52.216.165:30909"
backend = "vlm-http-client"
output_dir = "./parsed"

[api]
host = "0.0.0.0"
port = 8090
```

## MinerU 调用

使用 MinerU CLI 解析 PDF：

```bash
mineru -p ./paper.pdf -b vlm-http-client -u http://101.52.216.165:30909 -o ./res
```

输出文件：
- `*_middle.json` - 精确坐标（**重要**）
- `*_content_list.json` - 内容列表
- `*_content_list_v2.json` - v2 格式内容列表
- `*.md` - Markdown 文件
- `images/` - 提取的图片

## 依赖关系

```
md2tree
├── openai (LLM 调用)
├── tiktoken (Token 计数)
├── python-dotenv (环境变量)
├── tomli/tomllib (配置解析)
└── PyMuPDF (fitz) (PDF 操作)
```

## 扩展性

1. **新的 LLM 后端**: 实现 OpenAI 兼容接口即可
2. **新的 PDF 解析器**: 实现 `ContentBlock` 数据结构
3. **新的输出格式**: 基于树结构扩展
