# md2tree API 文档

## 目录

- [核心模块](#核心模块)
- [定位模块](#定位模块)
- [工作流模块](#工作流模块)
- [工具函数](#工具函数)

---

## 核心模块

### md2tree

#### `md_to_tree(md_path, add_node_id=True, keep_text=True, keep_fields=None)`

基础转换函数，将 Markdown 文件转换为树结构。

**参数:**
- `md_path` (str): Markdown 文件路径
- `add_node_id` (bool): 是否添加节点 ID，默认 `True`
- `keep_text` (bool): 是否保留文本内容，默认 `True`
- `keep_fields` (List[str], optional): 要保留的字段列表

**返回:**
```python
{
    "doc_name": "文档名称",
    "structure": [
        {
            "title": "章节标题",
            "node_id": "0001",
            "text": "章节内容...",
            "line_num": 1,
            "nodes": []
        }
    ]
}
```

**示例:**
```python
from md2tree import md_to_tree

tree_data = md_to_tree('document.md')
print(tree_data['doc_name'])
```

---

#### `md_to_tree_async(md_path, config=None, ...)`

高级异步转换函数，支持 LLM 功能。

**参数:**
- `md_path` (str): Markdown 文件路径
- `config` (LLMConfig, optional): LLM 配置
- `add_node_id` (bool): 是否添加节点 ID
- `keep_text` (bool): 是否保留文本内容
- `if_thinning` (bool): 是否应用树剪枝
- `thinning_threshold` (int): 剪枝阈值，默认 5000
- `if_add_node_summary` (bool): 是否生成摘要
- `summary_token_threshold` (int): 摘要阈值，默认 200
- `if_add_doc_description` (bool): 是否生成文档描述

**返回:**
```python
{
    "doc_name": "文档名称",
    "doc_description": "AI生成的描述",
    "structure": [...]
}
```

**示例:**
```python
import asyncio
from md2tree import md_to_tree_async, LLMConfig

config = LLMConfig(model="glm-4.7")
tree_data = asyncio.run(md_to_tree_async(
    'document.md',
    config=config,
    if_thinning=True,
    if_add_node_summary=True
))
```

---

### LLM 模块

#### `LLMConfig`

LLM 配置类。

```python
class LLMConfig:
    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = None,
        temperature: float = 0.0,
        max_retries: int = None,
        retry_delay: float = None
    )
```

**配置优先级:**
1. 显式传入的参数
2. config.toml 文件
3. 环境变量 (ZHIPU_API_KEY, OPENAI_API_KEY, etc.)

---

#### `call_llm(prompt, config=None, chat_history=None)`

同步 LLM 调用。

**参数:**
- `prompt` (str): 提示文本
- `config` (LLMConfig, optional): LLM 配置
- `chat_history` (List[dict], optional): 对话历史

**返回:** `str` - LLM 响应文本

---

#### `call_llm_async(prompt, config=None)`

异步 LLM 调用，带并发控制。

**参数:**
- `prompt` (str): 提示文本
- `config` (LLMConfig, optional): LLM 配置

**返回:** `str` - LLM 响应文本

---

#### `call_llm_async_batch(prompts, config=None, max_concurrent=None)`

批量异步 LLM 调用。

**参数:**
- `prompts` (List[str]): 提示文本列表
- `config` (LLMConfig, optional): LLM 配置
- `max_concurrent` (int, optional): 覆盖最大并发数

**返回:** `List[str]` - LLM 响应列表

---

## 定位模块

### MiddleJSONParser

解析 MinerU 的 middle.json 文件，获取精确的 PDF 坐标。

#### 初始化

```python
from md2tree.middle_json_parser import MiddleJSONParser

parser = MiddleJSONParser("path/to/middle.json")
```

---

#### `get_blocks_by_page(page_idx)`

获取指定页的所有块。

**参数:**
- `page_idx` (int): 页码（从 0 开始）

**返回:** `List[ParaBlock]` - 块列表

---

#### `find_blocks_by_text(search_text, fuzzy=False)`

查找包含指定文本的块。

**参数:**
- `search_text` (str): 搜索文本
- `fuzzy` (bool): 是否模糊匹配

**返回:** `List[ParaBlock]` - 匹配的块列表

**示例:**
```python
blocks = parser.find_blocks_by_text("memory wall", fuzzy=True)
for block in blocks:
    print(f"Page {block.page_idx + 1}, bbox: {block.bbox}")
```

---

#### `search_and_locate(query)`

搜索文本并返回详细位置信息。

**参数:**
- `query` (str): 搜索查询

**返回:**
```python
[
    {
        "page_idx": 0,
        "bbox": [45, 145, 301, 297],
        "type": "text",
        "context": "...匹配的上下文...",
        "match_position": 10,
        "full_info": {...}
    }
]
```

---

#### `locate_node_in_tree(node_title, node_text)`

定位树节点在 PDF 中的位置。

**参数:**
- `node_title` (str): 节点标题
- `node_text` (str): 节点文本

**返回:**
```python
{
    "title_block": {...},
    "content_blocks": [...],
    "page_range": (0, 2),
    "all_blocks": [...]
}
```

---

### MinerUParser

解析 MinerU 的 content_list.json（备用方案）。

#### 初始化

```python
from md2tree.mineru_parser import MinerUParser

parser = MinerUParser("path/to/content_list.json", pdf_path="path/to/pdf")
```

---

#### `find_text_location(search_text, fuzzy=False)`

查找文本在 PDF 中的位置。

**返回:**
```python
[
    {
        "page_idx": 0,
        "bbox": [45, 145, 301, 297],
        "pdf_bbox": [45.0, 145.0, 301.0, 297.0],
        "text": "匹配的文本...",
        "type": "text"
    }
]
```

---

### 辅助函数

#### `add_middlejson_location_to_tree(tree_structure, middle_json_path)`

使用 middle.json 为树结构添加位置信息。

```python
from md2tree.middle_json_parser import add_middlejson_location_to_tree

enhanced_tree = add_middlejson_location_to_tree(
    tree_data['structure'],
    'path/to/middle.json'
)
```

---

#### `add_location_info_to_tree(tree_structure, content_list_path, pdf_path=None)`

使用 content_list.json 为树结构添加位置信息。

```python
from md2tree.mineru_parser import add_location_info_to_tree

enhanced_tree = add_location_info_to_tree(
    tree_data['structure'],
    'path/to/content_list.json',
    pdf_path='path/to/pdf'
)
```

---

## 工作流模块

### PDFToTreeWorkflow

完整的 PDF 到树的工作流。

#### 初始化

```python
from md2tree.workflow import PDFToTreeWorkflow

workflow = PDFToTreeWorkflow(
    pdf_path="paper.pdf",
    mineru_output_dir="./res/paper/",
    use_middle_json=True  # 推荐使用 middle.json
)
```

---

#### `run_basic(output_path=None, add_node_id=True, keep_text=True)`

运行基础工作流（无需 LLM）。

**返回:**
```python
{
    "doc_name": "paper",
    "pdf_path": "paper.pdf",
    "pdf_name": "paper.pdf",
    "location_source": "middle.json",
    "stats": {
        "total_nodes": 15,
        "max_depth": 3,
        "leaf_nodes": 10
    },
    "structure": [...]
}
```

---

#### `run_advanced(...)`

运行高级工作流（带 LLM 功能）。

```python
result = await workflow.run_advanced(
    if_thinning=True,
    if_add_summary=True,
    if_add_doc_description=True,
    model="glm-4.7"
)
```

---

#### `search_and_locate_blocks(query, output_html=None, max_results=10)`

**核心功能**: 搜索文本并定位到具体的块。

**参数:**
- `query` (str): 搜索查询
- `output_html` (str, optional): 输出 HTML 路径
- `max_results` (int): 最大结果数

**返回:**
```python
{
    "query": "memory wall",
    "source": "middle.json",
    "total_results": 15,
    "returned_results": 10,
    "results": [
        {
            "rank": 1,
            "page_idx": 0,
            "page_num": 1,
            "bbox": [45, 145, 301, 297],
            "type": "text",
            "context": "...memory wall...",
            "pdf_link": "paper.pdf#page=1&bbox=45,145,301,297",
            "spans": [...]
        }
    ]
}
```

**示例:**
```python
results = workflow.search_and_locate_blocks(
    "arithmetic intensity",
    output_html="results/search.html"
)

for r in results['results']:
    print(f"Page {r['page_num']}: {r['context'][:50]}...")
```

---

#### `view_node(node_id, tree_data, output_html, output_pdf=None)`

查看节点在 PDF 中的位置。

**参数:**
- `node_id` (str): 节点 ID
- `tree_data` (dict): 树结构数据
- `output_html` (str): 输出 HTML 路径
- `output_pdf` (str, optional): 输出高亮 PDF 路径

---

### 快捷函数

#### `quick_process(pdf_path, mineru_output_dir, output_path=None)`

快速处理 PDF 到树的转换。

```python
from md2tree.workflow import quick_process

tree_data = quick_process(
    "paper.pdf",
    "./res/paper/",
    output_path="tree.json"
)
```

---

## 工具函数

### 树操作

#### `structure_to_list(structure)`

将树结构展平为节点列表。

```python
from md2tree.utils import structure_to_list

all_nodes = structure_to_list(tree_data['structure'])
print(f"Total nodes: {len(all_nodes)}")
```

---

#### `get_leaf_nodes(structure)`

获取所有叶子节点。

```python
from md2tree.utils import get_leaf_nodes

leaves = get_leaf_nodes(tree_data['structure'])
```

---

#### `find_node_by_id(structure, node_id)`

按 ID 查找节点。

```python
from md2tree.utils import find_node_by_id

node = find_node_by_id(tree_data['structure'], '0001')
if node:
    print(node['title'])
```

---

#### `find_node_by_title(structure, title)`

按标题查找节点。

```python
from md2tree.utils import find_node_by_title

node = find_node_by_title(tree_data['structure'], 'Introduction')
```

---

#### `get_tree_stats(structure)`

获取树统计信息。

**返回:**
```python
{
    "total_nodes": 15,
    "max_depth": 3,
    "leaf_nodes": 10,
    "internal_nodes": 5
}
```

---

#### `validate_tree(structure)`

验证树结构。

**返回:** `List[str]` - 问题列表（空列表表示有效）

---

### Token 计数

#### `count_tokens(text, model="gpt-4o")`

计算文本的 token 数量。

```python
from md2tree.llm import count_tokens

tokens = count_tokens("Hello, world!")
print(f"Tokens: {tokens}")
```

---

## 数据类型

### ParaBlock

```python
@dataclass
class ParaBlock:
    bbox: List[float]       # [x1, y1, x2, y2]
    type: str               # title, text, image, etc.
    angle: float            # 旋转角度
    lines: List[TextLine]   # 文本行
    index: int              # 块索引
    page_idx: int           # 页码
```

### ContentBlock

```python
@dataclass
class ContentBlock:
    type: str
    text: Optional[str]
    text_level: Optional[int]
    bbox: List[float]
    page_idx: int
    img_path: Optional[str]
    image_caption: Optional[List[str]]
    pdf_bbox: Optional[List[float]]
```
