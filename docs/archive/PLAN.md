# md2tree 项目优化计划

> 本文档基于 `CHECK.md` 审查报告，规划剩余 18 项待处理问题的实施方案。

## 📊 当前状态

| 指标 | 数值 |
|------|------|
| 已完成 | 35 项 |
| 待处理 | 11 项 |
| 完成率 | 76% |

### ✅ 本次完成的任务

| 任务 | 状态 | 新建文件 |
|------|------|----------|
| 1.1 统一文档字符串语言 | ✅ 完成 | - |
| 1.2 完善类型注解 | ✅ 完成 | `core/types.py` |
| 1.3 提取硬编码常量 | ✅ 完成 | `core/constants.py` |
| 2.1 重构全局状态管理 | ✅ 完成 | `core/context.py` |
| 2.2 解耦 openindex 模块 | ✅ 完成 | 更新 `__init__.py` |

---

## ✅ Phase 1: 代码质量提升（P2）- 已完成

**预计工时**: 2-3 天  
**优先级**: 中  
**风险**: 低  
**状态**: ✅ 已完成

### 1.1 统一文档字符串语言 (#10)

**目标**: 所有文档字符串使用中文（考虑项目主要面向中文用户）

**涉及文件**:
- `core/*.py`
- `llm/*.py`
- `parsers/*.py`
- `pdf/*.py`
- `openindex/*.py`

**执行步骤**:
```bash
# 1. 找出英文 docstring
grep -r '"""[A-Z]' md2tree/*.py --include="*.py"

# 2. 逐个文件统一修改
```

**规范模板**:
```python
def example_function(param1: str, param2: int) -> bool:
    """
    函数功能简述
    
    详细说明（可选）
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        返回值说明
        
    Raises:
        ExceptionType: 异常说明
    """
```

---

### 1.2 完善类型注解 (#11)

**目标**: 所有公开函数和方法添加完整类型注解

**重点文件**:
| 文件 | 优先级 | 状态 |
|------|--------|------|
| `core/converter.py` | 高 | 待处理 |
| `llm/client.py` | 高 | 待处理 |
| `openindex/query_service.py` | 高 | 待处理 |
| `parsers/base.py` | 中 | ✅ 已完成 |

**执行步骤**:
1. 安装 mypy: `pip install mypy`
2. 运行检查: `mypy md2tree/ --ignore-missing-imports`
3. 逐个修复类型错误

**类型定义示例**:
```python
# types.py (新建)
from typing import TypedDict, List, Dict, Optional

class TreeNode(TypedDict):
    title: str
    node_id: str
    text: str
    level: int
    line_num: int
    nodes: List['TreeNode']
    summary: Optional[str]
    page_info: Optional[Dict]

class TreeStructure(TypedDict):
    doc_name: str
    doc_description: Optional[str]
    structure: List[TreeNode]
```

---

### 1.3 提取硬编码常量 (#12)

**目标**: 将硬编码常量移至配置文件或常量模块

**当前问题**:
```python
# mineru_parser.py - 硬编码的 PDF 尺寸
self.pdf_width = 612
self.pdf_height = 792
self.mineru_width = 1000
self.mineru_height = 1000
```

**解决方案**:

```python
# core/constants.py (新建)
"""项目常量定义"""

# PDF 默认尺寸 (Letter 纸张)
PDF_DEFAULT_WIDTH = 612
PDF_DEFAULT_HEIGHT = 792

# MinerU 内部坐标系尺寸
MINERU_INTERNAL_WIDTH = 1000
MINERU_INTERNAL_HEIGHT = 1000

# 树处理默认值
DEFAULT_TOKEN_THRESHOLD = 5000
DEFAULT_SUMMARY_THRESHOLD = 200

# API 默认值
DEFAULT_TOP_K = 5
DEFAULT_MAX_HISTORY = 10
```

---

## ✅ Phase 2: 架构优化（P1-P2）- 已完成

**预计工时**: 3-5 天  
**优先级**: 中高  
**风险**: 中  
**状态**: ✅ 已完成

### 2.1 重构全局状态管理 (#4)

**目标**: 消除全局变量，使用依赖注入模式

**当前问题** (`llm/client.py`):
```python
_semaphore: Optional[asyncio.Semaphore] = None
_config_loaded = False
_config_data = {}
```

**解决方案**:

```python
# core/context.py (新建)
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class AppContext:
    """应用上下文，存储请求级别的状态"""
    config: dict
    semaphore: asyncio.Semaphore
    db: Optional['Database'] = None

# 使用 contextvars 管理并发状态
_current_context: ContextVar[AppContext] = ContextVar('app_context')

def get_context() -> AppContext:
    return _current_context.get()

def set_context(ctx: AppContext):
    _current_context.set(ctx)
```

**迁移步骤**:
1. 创建 `core/context.py`
2. 修改 `LLMConfig` 从 context 获取配置
3. 修改 `call_llm_async` 从 context 获取 semaphore
4. 在应用启动时初始化 context

---

### 2.2 解耦 openindex 模块 (#7)

**目标**: openindex 通过公开 API 使用 md2tree 功能

**当前问题**:
```python
# openindex/parser_service.py - 直接导入内部模块
from ..core.converter import md_to_tree
from ..parsers.middle_json import MiddleJSONParser
```

**解决方案**:

```python
# md2tree/__init__.py - 定义公开 API
__all__ = [
    # 核心转换
    'md_to_tree',
    'md_to_tree_async',
    
    # 工作流
    'run_advanced',
    
    # 解析器
    'MinerUParser',
    'MiddleJSONParser',
    
    # 配置
    'LLMConfig',
    'load_config',
    'get_config_value',
]

# openindex 只从包顶层导入
from md2tree import md_to_tree, MiddleJSONParser
```

---

## 🗄️ Phase 3: 数据存储优化（P1-P3）

**预计工时**: 5-7 天  
**优先级**: 中  
**风险**: 高（需要数据迁移）

### 3.1 目录结构重组 (#14, #15)

**目标**: 按文档 ID 组织所有相关文件

**当前结构**:
```
data/
├── uploads/      # PDF 原文件
├── parsed/       # MinerU 输出
└── trees/        # 树结构
```

**目标结构**:
```
data/
├── db/
│   └── openindex.db
└── documents/
    └── {doc_id}/
        ├── original.pdf
        ├── tree.json
        └── mineru/
            └── vlm/
                ├── content.md
                ├── middle.json
                └── images/
```

**迁移脚本**:
```python
# scripts/migrate_storage.py
import shutil
from pathlib import Path

def migrate_document(doc_id: str, old_data_dir: Path, new_data_dir: Path):
    """迁移单个文档到新结构"""
    new_doc_dir = new_data_dir / "documents" / doc_id
    new_doc_dir.mkdir(parents=True, exist_ok=True)
    
    # 迁移 PDF
    old_pdf = old_data_dir / "uploads" / f"{doc_id}_*.pdf"
    # ...
    
    # 迁移 tree.json
    old_tree = old_data_dir / "trees" / f"{doc_id}_tree.json"
    # ...
    
    # 迁移 MinerU 输出
    old_parsed = old_data_dir / "parsed" / doc_id
    # ...
```

---

### 3.2 路径存储改为相对路径 (#17)

**目标**: 数据库存储相对路径，便于数据迁移

**当前代码**:
```python
pdf_path = self.uploads_dir / pdf_filename  # 绝对路径
```

**修改方案**:
```python
# document_store.py
def add_document(self, filename: str, content: bytes):
    doc_id = str(uuid.uuid4())[:8]
    
    # 存储相对路径
    relative_path = f"documents/{doc_id}/original.pdf"
    full_path = self.data_dir / relative_path
    
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    
    # 数据库存储相对路径
    self.db.add_document(doc_id, name, filename, relative_path)

def get_pdf_path(self, doc_id: str) -> Path:
    """获取 PDF 完整路径"""
    doc = self.db.get_document(doc_id)
    return self.data_dir / doc['pdf_path']  # 拼接成绝对路径
```

---

### 3.3 简化 documents 表 (#18)

**目标**: 移除冗余字段，使用计算得出的路径

**当前表结构** (16 字段):
```sql
CREATE TABLE documents (
    id, name, original_filename, 
    pdf_path, md_path, tree_path, mineru_dir,  -- 冗余
    status, total_nodes, max_depth, total_pages, file_size,
    created_at, updated_at, parsed_at, metadata
);
```

**优化后** (10 字段):
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'parsing', 'ready', 'error')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsed_at TIMESTAMP
);

-- 路径通过约定计算
-- PDF: documents/{id}/original.pdf
-- Tree: documents/{id}/tree.json
-- MinerU: documents/{id}/mineru/
```

---

### 3.4 添加解析任务表 (#20)

**目标**: 记录解析历史，便于追踪和重试

```sql
CREATE TABLE parse_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    mineru_version TEXT,
    error_message TEXT,
    error_traceback TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_parse_jobs_doc ON parse_jobs(doc_id);
CREATE INDEX idx_parse_jobs_status ON parse_jobs(status);
```

---

### 3.5 数据库单例重构 (#22)

**目标**: 使用依赖注入替代全局单例

**当前代码**:
```python
_db_instance: Optional[Database] = None

def get_database() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance
```

**解决方案**:
```python
# FastAPI 依赖注入
from fastapi import Depends

def get_db():
    """数据库依赖"""
    db = Database(settings.db_path)
    try:
        yield db
    finally:
        db.close()

@app.get("/api/documents")
async def list_documents(db: Database = Depends(get_db)):
    return db.get_all_documents()
```

---

## 📈 Phase 4: 用户体验优化（P2）

**预计工时**: 2-3 天  
**优先级**: 低  
**风险**: 低

### 4.1 解析进度反馈 (#36)

**目标**: 提供细粒度的解析进度

**方案 A: 轮询模式**
```python
# 细化状态
class ParseStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PARSING_MINERU = "parsing_mineru"
    PARSING_MARKDOWN = "parsing_markdown"
    ADDING_LOCATIONS = "adding_locations"
    GENERATING_SUMMARY = "generating_summary"
    READY = "ready"
    ERROR = "error"

# API 返回进度
@app.get("/api/documents/{doc_id}/status")
async def get_parse_status(doc_id: str):
    return {
        "status": "parsing_markdown",
        "progress": 45,  # 百分比
        "stage": "正在转换 Markdown 为树结构",
        "estimated_remaining": 30  # 秒
    }
```

**方案 B: WebSocket 推送**
```python
@app.websocket("/ws/parse/{doc_id}")
async def parse_progress_ws(websocket: WebSocket, doc_id: str):
    await websocket.accept()
    while True:
        status = get_parse_status(doc_id)
        await websocket.send_json(status)
        if status['status'] in ('ready', 'error'):
            break
        await asyncio.sleep(1)
```

---

### 4.2 上传进度反馈 (#35)

**目标**: 大文件上传时显示进度

**前端方案** (使用 XMLHttpRequest):
```javascript
const xhr = new XMLHttpRequest();
xhr.upload.addEventListener('progress', (e) => {
    const percent = (e.loaded / e.total) * 100;
    updateProgressBar(percent);
});
```

**后端方案** (分块上传):
```python
@app.post("/api/documents/upload/chunk")
async def upload_chunk(
    file_id: str,
    chunk_index: int,
    total_chunks: int,
    chunk: UploadFile
):
    # 保存分块
    chunk_path = temp_dir / f"{file_id}_{chunk_index}"
    content = await chunk.read()
    chunk_path.write_bytes(content)
    
    # 检查是否全部上传完成
    if chunk_index == total_chunks - 1:
        # 合并分块
        await merge_chunks(file_id, total_chunks)
```

---

### 4.3 解析输出目录冲突 (#40)

**目标**: 支持重新解析，保留历史版本

**方案**:
```python
def get_output_dir(self, doc_id: str, version: int = None) -> Path:
    """获取解析输出目录"""
    base_dir = self.data_dir / "documents" / doc_id / "mineru"
    
    if version:
        return base_dir / f"v{version}"
    
    # 获取最新版本
    existing = list(base_dir.glob("v*"))
    if existing:
        latest = max(int(d.name[1:]) for d in existing)
        return base_dir / f"v{latest}"
    return base_dir / "v1"

def create_new_version(self, doc_id: str) -> Path:
    """创建新版本目录"""
    base_dir = self.data_dir / "documents" / doc_id / "mineru"
    existing = list(base_dir.glob("v*"))
    new_version = max((int(d.name[1:]) for d in existing), default=0) + 1
    new_dir = base_dir / f"v{new_version}"
    new_dir.mkdir(parents=True)
    return new_dir
```

---

## 📅 实施时间表

| 阶段 | 任务 | 工时 | 依赖 |
|------|------|------|------|
| **Phase 1** | 代码质量 | 2-3 天 | 无 |
| 1.1 | 统一文档字符串 | 1 天 | - |
| 1.2 | 完善类型注解 | 1 天 | - |
| 1.3 | 提取硬编码常量 | 0.5 天 | - |
| **Phase 2** | 架构优化 | 3-5 天 | Phase 1 |
| 2.1 | 重构全局状态 | 2 天 | - |
| 2.2 | 解耦 openindex | 1-2 天 | 2.1 |
| **Phase 3** | 数据存储 | 5-7 天 | Phase 2 |
| 3.1 | 目录结构重组 | 2 天 | - |
| 3.2 | 相对路径存储 | 1 天 | 3.1 |
| 3.3 | 简化 documents 表 | 1 天 | 3.2 |
| 3.4 | 添加任务表 | 1 天 | 3.3 |
| 3.5 | DB 依赖注入 | 1-2 天 | 3.4 |
| **Phase 4** | 用户体验 | 2-3 天 | Phase 3 |
| 4.1 | 解析进度反馈 | 1 天 | - |
| 4.2 | 上传进度反馈 | 1 天 | - |
| 4.3 | 版本管理 | 0.5 天 | 3.1 |

**总计**: 12-18 天

---

## ✅ 验收标准

### Phase 1 完成标准
- [x] `mypy md2tree/` 无错误
- [x] 所有公开函数有 docstring
- [x] 无硬编码的魔法数字 → `core/constants.py`

### Phase 2 完成标准
- [x] 上下文管理替代全局状态 → `core/context.py`
- [x] openindex 只使用 `md2tree` 公开 API
- [ ] 单元测试可以独立运行

### Phase 3 完成标准
- [ ] 数据迁移脚本通过测试
- [ ] 新旧数据兼容
- [ ] 数据库 schema 版本控制

### Phase 4 完成标准
- [ ] 前端显示上传/解析进度
- [ ] 支持重新解析文档
- [ ] 解析历史可追溯

---

## 🔧 工具与命令

```bash
# 类型检查
mypy md2tree/ --ignore-missing-imports

# 代码格式化
ruff format md2tree/

# 代码检查
ruff check md2tree/

# 运行测试
pytest md2tree/tests/ -v

# 数据迁移
python -m md2tree.scripts.migrate_storage --dry-run
python -m md2tree.scripts.migrate_storage --execute
```

---

## 📚 Phase 5: 文档管理功能增强（新功能）

**预计工时**: 3-5 天  
**优先级**: 高  
**风险**: 中（涉及数据库结构变更）

### 5.1 前端 PDF 删除功能

**目标**: 在前端界面添加文档删除按钮

**当前状态**:
- ✅ 后端 API 已实现: `DELETE /api/documents/{doc_id}`
- ❌ 前端界面缺少删除按钮

**实现方案**:

```html
<!-- index.html - 文件列表项添加删除按钮 -->
<div class="file-item" onclick="selectDocument('${doc.id}')">
    <div class="file-name">
        <span class="file-icon">📑</span>
        <span>${doc.name}</span>
        <button class="delete-btn" onclick="event.stopPropagation(); deleteDocument('${doc.id}', '${doc.name}')">
            🗑️
        </button>
    </div>
    ...
</div>
```

```javascript
// 删除文档函数
async function deleteDocument(docId, docName) {
    if (!confirm(`确定要删除文档 "${docName}" 吗？\n\n删除后将同时清除：\n- PDF 原文件\n- 解析结果\n- 所有对话记录`)) {
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
            method: 'DELETE'
        });
        
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Delete failed');
        }
        
        // 刷新文档列表
        await loadDocuments();
        
        // 如果删除的是当前选中的文档，清空聊天界面
        if (state.currentDoc?.id === docId) {
            state.currentDoc = null;
            state.messages = [];
            state.references = [];
            showWelcomeMessage();
        }
        
        alert('文档已删除');
    } catch (err) {
        alert('删除失败：' + err.message);
    }
}
```

**CSS 样式**:
```css
.delete-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
    padding: 4px 8px;
    border-radius: 4px;
    margin-left: auto;
}

.file-item:hover .delete-btn {
    opacity: 0.6;
}

.delete-btn:hover {
    opacity: 1;
    background: rgba(251, 113, 133, 0.2);
}
```

---

### 5.2 文档库 (Library) 管理功能

**目标**: 添加"库"概念，支持将多个 PDF 文档归类到不同的库中

**数据库设计**:

```sql
-- 新增 libraries 表
CREATE TABLE libraries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#4dabf7',  -- 库的主题色
    icon TEXT DEFAULT '📁',        -- 库的图标
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- documents 表添加 library_id 字段
ALTER TABLE documents ADD COLUMN library_id TEXT REFERENCES libraries(id) ON DELETE SET NULL;

-- 创建索引
CREATE INDEX idx_documents_library ON documents(library_id);
```

**API 设计**:

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/libraries` | 创建库 |
| `GET` | `/api/libraries` | 列出所有库 |
| `GET` | `/api/libraries/{id}` | 获取库详情 |
| `PUT` | `/api/libraries/{id}` | 更新库信息 |
| `DELETE` | `/api/libraries/{id}` | 删除库（文档移至"未分类"） |
| `GET` | `/api/libraries/{id}/documents` | 获取库中的文档 |
| `POST` | `/api/documents/{doc_id}/move` | 移动文档到指定库 |

**Pydantic 模型**:

```python
# models.py

class LibraryCreate(BaseModel):
    """创建库请求"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    color: Optional[str] = Field(default='#4dabf7', pattern='^#[0-9a-fA-F]{6}$')
    icon: Optional[str] = Field(default='📁', max_length=2)

class LibraryUpdate(BaseModel):
    """更新库请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    color: Optional[str] = Field(default=None, pattern='^#[0-9a-fA-F]{6}$')
    icon: Optional[str] = Field(default=None, max_length=2)

class LibraryResponse(BaseModel):
    """库响应"""
    id: str
    name: str
    description: Optional[str]
    color: str
    icon: str
    document_count: int = 0
    created_at: str
    updated_at: str

class DocumentMoveRequest(BaseModel):
    """移动文档请求"""
    library_id: Optional[str] = None  # None 表示移至"未分类"
```

**后端实现**:

```python
# database.py - 添加 Library 相关方法

class Database:
    def _init_db(self):
        # ... 现有代码 ...
        
        # 库表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS libraries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#4dabf7',
                icon TEXT DEFAULT '📁',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 添加 library_id 字段到 documents 表
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN library_id TEXT REFERENCES libraries(id) ON DELETE SET NULL")
        except sqlite3.OperationalError:
            pass
    
    # ============= 库管理 =============
    
    def create_library(self, name: str, description: str = None, color: str = '#4dabf7', icon: str = '📁') -> Dict:
        lib_id = str(uuid.uuid4())[:8]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO libraries (id, name, description, color, icon)
                VALUES (?, ?, ?, ?, ?)
            """, (lib_id, name, description, color, icon))
        return self.get_library(lib_id)
    
    def get_library(self, lib_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM libraries WHERE id = ?", (lib_id,))
            row = cursor.fetchone()
            if row:
                lib = self._row_to_dict(row)
                # 获取文档数量
                cursor.execute("SELECT COUNT(*) FROM documents WHERE library_id = ?", (lib_id,))
                lib['document_count'] = cursor.fetchone()[0]
                return lib
        return None
    
    def get_all_libraries(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM libraries ORDER BY name")
            libraries = []
            for row in cursor.fetchall():
                lib = self._row_to_dict(row)
                cursor.execute("SELECT COUNT(*) FROM documents WHERE library_id = ?", (lib['id'],))
                lib['document_count'] = cursor.fetchone()[0]
                libraries.append(lib)
            return libraries
    
    def update_library(self, lib_id: str, **kwargs) -> bool:
        if not kwargs:
            return False
        kwargs['updated_at'] = datetime.now().isoformat()
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [lib_id]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE libraries SET {fields} WHERE id = ?", values)
            return cursor.rowcount > 0
    
    def delete_library(self, lib_id: str) -> bool:
        # 文档的 library_id 会被设为 NULL (ON DELETE SET NULL)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM libraries WHERE id = ?", (lib_id,))
            return cursor.rowcount > 0
    
    def move_document_to_library(self, doc_id: str, library_id: Optional[str]) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET library_id = ?, updated_at = ? WHERE id = ?",
                (library_id, datetime.now().isoformat(), doc_id)
            )
            return cursor.rowcount > 0
    
    def get_documents_by_library(self, library_id: Optional[str]) -> List[Dict]:
        """获取库中的文档，library_id 为 None 时获取未分类文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if library_id:
                cursor.execute("SELECT * FROM documents WHERE library_id = ? ORDER BY created_at DESC", (library_id,))
            else:
                cursor.execute("SELECT * FROM documents WHERE library_id IS NULL ORDER BY created_at DESC")
            return [self._row_to_dict(row) for row in cursor.fetchall()]
```

**前端界面设计**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  OpenIndex                                                    🟢 服务运行中  │
├──────────────────┬────────────────────────────────┬─────────────────────────┤
│  文档库          │  对话区域                       │  引用来源               │
│  ──────────────  │                                │                         │
│  + 新建库        │                                │                         │
│                  │                                │                         │
│  📁 机器学习 (5) │                                │                         │
│    📑 论文1      │                                │                         │
│    📑 论文2  🗑️  │                                │                         │
│                  │                                │                         │
│  📁 生物医学 (3) │                                │                         │
│    📑 DNA研究    │                                │                         │
│                  │                                │                         │
│  📂 未分类 (2)   │                                │                         │
│    📑 新论文     │                                │                         │
│                  │                                │                         │
│  ──────────────  │                                │                         │
│  + 上传          │                                │                         │
└──────────────────┴────────────────────────────────┴─────────────────────────┘
```

**前端实现要点**:

1. **左侧边栏改为两级结构**: 库 -> 文档
2. **库的操作**: 创建、重命名、删除、更换颜色/图标
3. **文档操作**: 删除、移动到其他库
4. **拖拽支持**: 可拖拽文档到其他库
5. **上传时选择库**: 上传对话框中可选择目标库

**JavaScript 状态管理**:

```javascript
const state = {
    libraries: [],           // 库列表
    currentLibrary: null,    // 当前选中的库 (null = 未分类)
    documents: [],           // 当前库的文档列表
    currentDoc: null,        // 当前选中的文档
    // ... 其他状态
};

// 加载库列表
async function loadLibraries() {
    const res = await fetch(`${API_BASE}/api/libraries`);
    state.libraries = await res.json();
    renderLibraryList();
}

// 选择库
async function selectLibrary(libId) {
    state.currentLibrary = libId;
    const endpoint = libId 
        ? `${API_BASE}/api/libraries/${libId}/documents`
        : `${API_BASE}/api/documents?library_id=null`;
    const res = await fetch(endpoint);
    state.documents = await res.json();
    renderFileList();
}
```

---

### 5.3 实施步骤

| 步骤 | 任务 | 工时 | 依赖 |
|------|------|------|------|
| 5.1.1 | 前端删除按钮 UI | 0.5 天 | - |
| 5.1.2 | 删除确认对话框 | 0.5 天 | 5.1.1 |
| 5.2.1 | 数据库 schema 更新 | 0.5 天 | - |
| 5.2.2 | 后端 Library API | 1 天 | 5.2.1 |
| 5.2.3 | 前端库管理 UI | 1.5 天 | 5.2.2 |
| 5.2.4 | 文档移动功能 | 0.5 天 | 5.2.3 |
| 5.2.5 | 拖拽支持（可选） | 0.5 天 | 5.2.4 |

**总计**: 3-5 天

---

### 5.4 验收标准

- [ ] 前端可删除文档，删除前有确认对话框
- [ ] 删除文档后自动刷新列表
- [ ] 可创建、编辑、删除库
- [ ] 可将文档移动到指定库
- [ ] "未分类"库显示没有归属的文档
- [ ] 库列表显示每个库的文档数量
- [ ] 删除库后，其中的文档移至"未分类"

---

## 📅 更新后的实施时间表

| 阶段 | 任务 | 工时 | 状态 |
|------|------|------|------|
| **Phase 1** | 代码质量 | 2-3 天 | ✅ 已完成 |
| **Phase 2** | 架构优化 | 3-5 天 | ✅ 已完成 |
| **Phase 3** | 数据存储 | 5-7 天 | ⏳ 待开始 |
| **Phase 4** | 用户体验 | 2-3 天 | ⏳ 待开始 |
| **Phase 5** | 文档管理增强 | 3-5 天 | ⏳ 待开始 |

**总计**: 15-23 天

---

*计划创建时间: 2026-01-12*  
*最后更新: 2026-01-12*  
*基于: CHECK.md v2.2.0*
