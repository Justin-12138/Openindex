"""
OpenIndex FastAPI 应用

AI 论文阅读应用的 Web API。
"""

import logging
import asyncio
import uuid
import time
from pathlib import Path
from typing import List, Optional
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from .models import (
    DocumentStatus, UploadResponse, 
    QueryRequest, QueryResponse, SearchRequest, SearchResponse,
    TreeResponse
)
from .document_store import DocumentStore
from .parser_service import ParserService
from .query_service import QueryService

# 导入配置 - 使用相对导入
from ..llm import load_config, get_config_value

logger = logging.getLogger(__name__)

# 请求ID追踪
_request_id: ContextVar[str] = ContextVar('request_id', default=None)

# 加载配置
load_config()

# 尝试导入速率限制（可选）
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _rate_limiting_available = True
except ImportError:
    _rate_limiting_available = False
    logger.warning("slowapi not installed, rate limiting disabled. Install with: pip install slowapi")

# 初始化应用
app = FastAPI(
    title="OpenIndex",
    description="AI 论文阅读应用 - 智能检索与 PDF 定位",
    version="0.2.0"
)

# 添加速率限制（如果可用）
if _rate_limiting_available:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    def rate_limit(limit: str):
        """速率限制装饰器"""
        return limiter.limit(limit)
else:
    def rate_limit(limit: str):
        """速率限制装饰器（未安装 slowapi 时为空操作）"""
        def decorator(func):
            return func
        return decorator

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= 中间件 =============

@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    """
    为每个请求添加唯一ID并记录请求日志
    
    功能：
    - 生成请求ID
    - 记录请求开始时间
    - 记录请求日志（方法、路径、状态码、响应时间）
    """
    request_id = str(uuid.uuid4())[:8]
    _request_id.set(request_id)
    
    # 记录请求开始时间
    start_time = time.time()
    
    # 记录请求信息
    logger.info(
        f"Request started: {request.method} {request.url.path} "
        f"(Request ID: {request_id}, Client: {request.client.host if request.client else 'unknown'})"
    )
    
    try:
        # 处理请求
        response = await call_next(request)
        
        # 计算响应时间
        process_time = time.time() - start_time
        
        # 将请求ID和响应时间添加到响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        # 记录请求完成信息
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Time: {process_time:.4f}s "
            f"(Request ID: {request_id})"
        )
        
        return response
        
    except Exception as e:
        # 计算错误响应时间
        process_time = time.time() - start_time
        
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"Error: {str(e)} "
            f"Time: {process_time:.4f}s "
            f"(Request ID: {request_id})"
        )
        raise


# ============= 全局异常处理 =============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    request_id = _request_id.get()
    logger.warning(
        f"HTTP {exc.status_code} error: {exc.detail} "
        f"(Request ID: {request_id}, Path: {request.url.path})"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": request_id,
                "path": str(request.url.path),
            }
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    request_id = _request_id.get()
    logger.warning(
        f"Validation error: {exc.errors()} "
        f"(Request ID: {request_id}, Path: {request.url.path})"
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": exc.errors(),
                "request_id": request_id,
                "path": str(request.url.path),
            }
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    import traceback
    request_id = _request_id.get()
    error_traceback = traceback.format_exc()
    
    logger.error(
        f"Unhandled exception: {str(exc)}\n{error_traceback} "
        f"(Request ID: {request_id}, Path: {request.url.path})"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "request_id": request_id,
                "path": str(request.url.path),
            }
        },
        headers={"X-Request-ID": request_id}
    )

# 数据目录
DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"

# 初始化服务
document_store = DocumentStore(str(DATA_DIR))
parser_service = ParserService(document_store)
query_service = QueryService(document_store)

# 解析任务队列和并发控制
_parse_semaphore = asyncio.Semaphore(
    get_config_value('app', 'max_concurrent_parsing', 2)  # 默认最多 2 个并发解析任务
)

# 挂载静态文件
if STATIC_DIR.exists():
    # 挂载 assets 目录用于 JS/CSS
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    # 保留原 /static 挂载点以保持兼容
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============= Pydantic 模型 =============

class DocumentResponse(BaseModel):
    id: str
    name: str
    status: str
    stats: Optional[dict] = None
    pdf_path: Optional[str] = None
    created_at: Optional[str] = None
    file_size: Optional[int] = None
    library_id: Optional[str] = None


class ConversationCreate(BaseModel):
    doc_id: str
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    doc_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0
    messages: Optional[List[dict]] = None


class MessageCreate(BaseModel):
    conversation_id: str
    role: str
    content: str
    references: Optional[List[dict]] = None
    selected_nodes: Optional[List[dict]] = None
    locations: Optional[List[dict]] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: str
    role: str
    content: str
    references: Optional[List[dict]] = None
    created_at: Optional[str] = None


class StatsResponse(BaseModel):
    total_documents: int
    ready_documents: int
    total_conversations: int
    total_messages: int


class LibraryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = '#4dabf7'
    icon: Optional[str] = '📁'


class LibraryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class LibraryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    color: str
    icon: str
    document_count: int = 0
    created_at: str
    updated_at: str


class DocumentMoveRequest(BaseModel):
    library_id: Optional[str] = None


# ============= 页面路由 =============

@app.get("/", response_class=HTMLResponse)
async def index():
    """首页"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(content="""
    <html>
        <head><title>OpenIndex</title></head>
        <body>
            <h1>OpenIndex - AI 论文阅读应用</h1>
            <p>请访问 <a href="/docs">/docs</a> 查看 API 文档</p>
        </body>
    </html>
    """)


# ============= 文档管理 API =============

# 从配置获取最大文件大小（默认 100MB）
MAX_FILE_SIZE = get_config_value('app', 'max_file_size', 100 * 1024 * 1024)


@app.post("/api/documents/upload", response_model=UploadResponse)
@rate_limit("10/minute")  # 每分钟最多 10 次上传
async def upload_document(file: UploadFile = File(...)):
    """
    上传 PDF 文档
    
    上传一个 PDF 文件到系统。文件会被保存到服务器，并创建文档记录。
    
    **限制**:
    - 文件大小: 最大 100MB（可在配置中调整）
    - 文件类型: 仅支持 PDF 文件
    - 文件名长度: 最大 255 字符
    - 速率限制: 每分钟最多 10 次上传
    
    **返回**:
    - `doc_id`: 文档唯一标识符
    - `name`: 文档名称
    - `status`: 文档状态（初始为 'pending'）
    - `file_size`: 文件大小（字节）
    - `created_at`: 创建时间
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8090/api/documents/upload" \\
      -F "file=@document.pdf"
    ```
    """
    # 验证文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    max_filename_length = get_config_value('app', 'max_filename_length', 255)
    if len(file.filename) > max_filename_length:
        raise HTTPException(
            status_code=400, 
            detail=f"Filename too long (max {max_filename_length} characters)"
        )
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # 分块读取文件并检查大小
    content = b""
    chunk_size = 1024 * 1024  # 1MB chunks
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content += chunk
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )
    
    # 验证 PDF 文件头
    if not content.startswith(b'%PDF'):
        raise HTTPException(status_code=400, detail="Invalid PDF file format")

    doc = document_store.add_document(file.filename, content)

    return UploadResponse(
        doc_id=doc['id'],
        name=doc['name'],
        status=doc['status'],
        message=f"Document uploaded successfully. Use /api/documents/{doc['id']}/parse to start parsing."
    )


@app.get("/api/documents", response_model=List[DocumentResponse])
async def list_documents():
    """
    获取所有文档列表
    
    返回系统中所有文档的列表，包括文档的基本信息和状态。
    
    **返回字段**:
    - `id`: 文档 ID
    - `name`: 文档名称
    - `status`: 文档状态（pending, parsing, ready, error）
    - `file_size`: 文件大小
    - `created_at`: 创建时间
    - `updated_at`: 更新时间
    
    **状态说明**:
    - `pending`: 等待解析
    - `parsing`: 正在解析
    - `ready`: 解析完成，可以查询
    - `error`: 解析失败
    """
    docs = document_store.get_all_documents()
    return [DocumentResponse(**doc) for doc in docs]


@app.get("/api/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """
    获取单个文档的详细信息
    
    **参数**:
    - `doc_id`: 文档唯一标识符（8位十六进制字符串）
    
    **返回**: 文档的完整信息，包括状态、元数据等
    
    **错误**:
    - 400: 文档ID格式无效
    - 404: 文档不存在
    """
    # 验证文档ID格式
    from .utils import validate_doc_id
    if not validate_doc_id(doc_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid document ID format: {doc_id}. Expected 8-character hexadecimal string."
        )
    
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**doc)


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除文档及所有相关文件
    
    删除内容：
    - PDF 原文件
    - MD 文件
    - 树结构 JSON 文件
    - MinerU 解析输出目录（middle.json、content_list.json、images 等）
    - 关联的对话和消息记录（数据库级联删除）
    """
    # 先获取文档信息用于返回
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_name = doc.get('name', doc_id)
    
    if not document_store.delete_document(doc_id):
        raise HTTPException(status_code=500, detail="Failed to delete document")
    
    return {
        "message": f"Document '{doc_name}' deleted successfully",
        "doc_id": doc_id,
        "deleted_items": [
            "PDF file",
            "Markdown file",
            "Tree structure JSON",
            "MinerU parsed output",
            "Related conversations and messages"
        ]
    }


# ============= 库管理 API =============

@app.post("/api/libraries", response_model=LibraryResponse)
async def create_library(request: LibraryCreate):
    """创建文档库"""
    lib = document_store.create_library(
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon
    )
    return LibraryResponse(**lib)


@app.get("/api/libraries", response_model=List[LibraryResponse])
async def list_libraries():
    """列出所有文档库"""
    libraries = document_store.get_all_libraries()
    return [LibraryResponse(**lib) for lib in libraries]


@app.get("/api/libraries/{lib_id}", response_model=LibraryResponse)
async def get_library(lib_id: str):
    """
    获取文档库信息
    
    **参数**:
    - `lib_id`: 库ID（UUID格式）或 "uncategorized"
    
    **返回**: 库的详细信息，包括文档数量
    
    **错误**:
    - 400: 库ID格式无效
    - 404: 库不存在
    """
    # 验证库ID格式
    from .utils import validate_library_id
    if not validate_library_id(lib_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid library ID format: {lib_id}"
        )
    lib = document_store.get_library(lib_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    return LibraryResponse(**lib)


@app.put("/api/libraries/{lib_id}", response_model=LibraryResponse)
async def update_library(lib_id: str, request: LibraryUpdate):
    """更新库信息"""
    lib = document_store.get_library(lib_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        document_store.update_library(lib_id, **update_data)
    
    return LibraryResponse(**document_store.get_library(lib_id))


@app.delete("/api/libraries/{lib_id}")
async def delete_library(lib_id: str):
    """
    删除文档库
    
    库中的文档会自动移至"未分类"
    """
    lib = document_store.get_library(lib_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    
    lib_name = lib.get('name', lib_id)
    doc_count = lib.get('document_count', 0)
    
    if not document_store.delete_library(lib_id):
        raise HTTPException(status_code=500, detail="Failed to delete library")
    
    return {
        "message": f"Library '{lib_name}' deleted successfully",
        "lib_id": lib_id,
        "documents_moved_to_uncategorized": doc_count
    }


@app.get("/api/libraries/{lib_id}/documents", response_model=List[DocumentResponse])
async def list_library_documents(lib_id: str):
    """获取库中的文档"""
    lib = document_store.get_library(lib_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    
    docs = document_store.get_documents_by_library(lib_id)
    return [DocumentResponse(**doc) for doc in docs]


@app.get("/api/documents/uncategorized", response_model=List[DocumentResponse])
async def list_uncategorized_documents():
    """获取未分类的文档"""
    docs = document_store.get_documents_by_library(None)
    return [DocumentResponse(**doc) for doc in docs]


@app.post("/api/documents/{doc_id}/move")
async def move_document(doc_id: str, request: DocumentMoveRequest):
    """
    移动文档到指定库
    
    **参数**:
    - `doc_id`: 文档ID（必填）
    - `library_id`: 目标库ID（可选，如果为 None 则移至"未分类"）
    
    **返回**:
    - `message`: 操作结果消息
    - `doc_id`: 文档ID
    - `library_id`: 目标库ID
    
    **错误**:
    - 400: 文档ID格式无效
    - 404: 文档不存在或目标库不存在
    - 500: 移动失败
    """
    # 验证文档ID格式
    from .utils import validate_doc_id
    if not validate_doc_id(doc_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document ID format: {doc_id}"
        )
    
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 如果指定了库 ID，验证格式并检查库是否存在
    if request.library_id:
        from .utils import validate_library_id
        if not validate_library_id(request.library_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid library ID format: {request.library_id}"
            )
        lib = document_store.get_library(request.library_id)
        if not lib:
            raise HTTPException(status_code=404, detail="Target library not found")
    
    if not document_store.move_document_to_library(doc_id, request.library_id):
        raise HTTPException(status_code=500, detail="Failed to move document")
    
    target = request.library_id if request.library_id else "未分类"
    return {
        "message": f"Document moved to '{target}'",
        "doc_id": doc_id,
        "library_id": request.library_id
    }


# ============= 解析 API =============

@app.post("/api/documents/{doc_id}/parse")
async def parse_document(doc_id: str, background_tasks: BackgroundTasks):
    """
    解析文档（异步，带并发控制）
    
    启动文档的解析流程，包括：
    1. 调用 MinerU 提取 PDF 内容
    2. 将 Markdown 转换为树结构
    3. 添加位置信息
    
    **参数**:
    - `doc_id`: 文档唯一标识符
    
    **说明**:
    - 解析是异步进行的，不会阻塞请求
    - 系统会限制并发解析任务数量（默认 2 个）
    - 解析状态会实时更新，可通过文档状态 API 查询
    
    **返回**:
    - `message`: 操作结果消息
    - `status`: 当前状态
    - `doc_id`: 文档 ID
    
    **错误**:
    - 404: 文档不存在
    - 400: 文档已在解析中或已解析完成
    """
    # 验证文档ID格式
    from .utils import validate_doc_id
    if not validate_doc_id(doc_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document ID format: {doc_id}"
        )
    
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    status = doc['status']
    if status in ('parsing', 'parsing_mineru', 'parsing_markdown', 'adding_locations'):
        return {
            "message": "Document is already being parsed",
            "status": status,
            "doc_id": doc_id
        }

    if status == 'ready':
        return {
            "message": "Document already parsed",
            "status": status,
            "doc_id": doc_id
        }

    # 异步解析（带并发控制）
    background_tasks.add_task(_parse_document_task_with_semaphore, doc_id)

    return {
        "message": "Parsing started",
        "status": "parsing",
        "doc_id": doc_id
    }


async def _parse_document_task_with_semaphore(doc_id: str):
    """解析任务（带并发控制）"""
    async with _parse_semaphore:
        await _parse_document_task(doc_id)


async def _parse_document_task(doc_id: str):
    """解析任务"""
    import traceback
    try:
        await parser_service.parse_document(doc_id)
        logger.info(f"Document {doc_id} parsed successfully")
    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Failed to parse document {doc_id}: {error_message}\n{error_traceback}")
        # 保存错误信息到数据库
        document_store.update_document_status(
            doc_id, 
            DocumentStatus.ERROR,
            error_message=f"{error_message}\n\n{error_traceback}"
        )


@app.get("/api/documents/{doc_id}/tree", response_model=TreeResponse)
async def get_tree(doc_id: str):
    """
    获取文档树结构
    
    **参数**:
    - `doc_id`: 文档ID（必填）
    
    **返回**: 文档的树结构，包括所有节点和统计信息
    
    **错误**:
    - 400: 文档ID格式无效
    - 404: 文档不存在或树结构不存在
    """
    # 验证文档ID格式
    from .utils import validate_doc_id
    if not validate_doc_id(doc_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document ID format: {doc_id}"
        )
    
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc['status'] != 'ready':
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready. Current status: {doc['status']}"
        )

    tree_data = document_store.load_tree(doc_id)
    if not tree_data:
        raise HTTPException(status_code=404, detail="Tree data not found")

    return TreeResponse(
        doc_id=doc_id,
        doc_name=doc['name'],
        structure=tree_data['structure'],
        stats=tree_data.get('stats', {})
    )


# ============= 对话 API =============

@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreate):
    """创建新对话"""
    doc = document_store.get_document(request.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    conv = document_store.create_conversation(request.doc_id, request.title)
    return ConversationResponse(**conv)


@app.get("/api/documents/{doc_id}/conversations", response_model=List[ConversationResponse])
async def list_conversations(doc_id: str):
    """
    获取文档的所有对话
    
    **参数**:
    - `doc_id`: 文档ID（必填）
    
    **返回**: 文档的所有对话列表
    
    **错误**:
    - 400: 文档ID格式无效
    - 404: 文档不存在
    """
    # 验证文档ID格式
    from .utils import validate_doc_id
    if not validate_doc_id(doc_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document ID format: {doc_id}"
        )
    
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    conversations = document_store.get_conversations(doc_id)
    return [ConversationResponse(**conv) for conv in conversations]


@app.get("/api/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: str):
    """
    获取对话详情（含消息历史）
    
    **参数**:
    - `conv_id`: 对话ID（UUID格式）
    
    **返回**: 对话的完整信息，包括所有消息
    
    **错误**:
    - 400: 对话ID格式无效
    - 404: 对话不存在
    """
    # 验证对话ID格式
    from .utils import validate_conversation_id
    if not validate_conversation_id(conv_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid conversation ID format: {conv_id}"
        )
    conv = document_store.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(**conv)


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除对话"""
    if not document_store.delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}


@app.post("/api/messages", response_model=MessageResponse)
async def add_message(request: MessageCreate):
    """添加消息到对话"""
    conv = document_store.get_conversation(request.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = document_store.add_message(
        conversation_id=request.conversation_id,
        role=request.role,
        content=request.content,
        references=request.references,
        selected_nodes=request.selected_nodes,
        locations=request.locations
    )
    return MessageResponse(**msg)


# ============= 查询 API =============

@app.post("/api/query", response_model=QueryResponse)
@rate_limit("30/minute")  # 每分钟最多 30 次查询
async def query_document(request: QueryRequest):
    """
    查询文档（智能问答）
    
    对文档进行智能查询，使用两阶段查询流程：
    1. **节点选择**: Query + 树结构 → LLM → 选择相关节点
    2. **答案生成**: Query + 节点原文 → LLM → 生成答案
    
    **参数**:
    - `doc_id`: 文档 ID（必填）
    - `query`: 查询文本（必填，最大 5000 字符）
    - `top_k`: 返回的相关节点数量（默认 5，范围 1-20）
    - `conversation_id`: 对话 ID（可选，用于上下文）
    - `parse_version`: 解析版本（可选，默认使用最新版本）
    
    **返回**:
    - `answer`: LLM 生成的答案
    - `sources`: 引用的文档节点列表
    - `conversation_id`: 对话 ID（如果创建了新对话）
    - `message_id`: 消息 ID
    
    **限制**:
    - 查询长度: 最大 5000 字符
    - 速率限制: 每分钟最多 30 次查询
    - 文档状态: 必须是 'ready' 状态
    
    **示例**:
    ```json
    {
      "doc_id": "abc123",
      "query": "这篇论文的主要贡献是什么？",
      "top_k": 5,
      "conversation_id": "conv456"
    }
    ```
    """
    # 验证查询长度（Pydantic 已经验证，这里再次确认）
    if len(request.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    max_query_length = get_config_value('app', 'max_query_length', 5000)
    if len(request.query) > max_query_length:
        raise HTTPException(
            status_code=400, 
            detail=f"Query too long (max {max_query_length} characters)"
        )
    
    doc = document_store.get_document(request.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc['status'] != 'ready':
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready. Current status: {doc['status']}"
        )

    try:
        # 消息保存现在由服务层自动处理
        response = query_service.query(
            doc_id=request.doc_id,
            query=request.query,
            top_k=request.top_k,
            conversation_id=request.conversation_id,
            save_to_conversation=True  # 自动保存消息到对话
        )
        return response
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=SearchResponse)
async def search_document(request: SearchRequest):
    """
    搜索文档中的文本块
    
    在文档中直接搜索文本，返回匹配的文本块及其位置信息。
    与 `/api/query` 不同，此接口不经过 LLM，直接返回匹配结果。
    
    **参数**:
    - `doc_id`: 文档 ID（必填）
    - `query`: 搜索关键词（必填）
    - `max_results`: 最大返回结果数（默认 10，范围 1-50）
    - `parse_version`: 解析版本（可选）
    
    **返回**:
    - `results`: 匹配的文本块列表
    - `total`: 总匹配数
    
    **适用场景**:
    - 精确文本搜索
    - 不需要 LLM 理解的简单查询
    - 需要快速响应的场景
    """
    doc = document_store.get_document(request.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc['status'] != 'ready':
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready. Current status: {doc['status']}"
        )

    try:
        response = query_service.search_blocks(
            doc_id=request.doc_id,
            query=request.query,
            max_results=request.max_results
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= PDF 访问 =============

@app.get("/api/documents/{doc_id}/pdf")
async def get_pdf(doc_id: str):
    """获取 PDF 文件"""
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_path = Path(doc.get('pdf_path', ''))
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    try:
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=pdf_path.name
        )
    except (IOError, OSError) as e:
        logger.error(f"Failed to read PDF file {pdf_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read PDF file: {e}")


# ============= 统计 API =============

@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """
    获取系统统计信息
    
    返回系统的详细统计信息，包括文档、对话、消息等。
    
    **返回字段**:
    - `total_documents`: 总文档数
    - `ready_documents`: 就绪文档数
    - `total_conversations`: 总对话数
    - `total_messages`: 总消息数
    """
    stats = document_store.get_stats()
    return StatsResponse(**stats)


# ============= 健康检查和监控 =============

@app.get("/health")
async def health_check():
    """
    健康检查端点
    
    返回系统健康状态，可用于负载均衡器和监控系统。
    
    **返回字段**:
    - `status`: 系统状态（healthy/unhealthy）
    - `version`: 系统版本
    - `timestamp`: 检查时间戳
    
    **状态码**:
    - 200: 系统健康
    - 503: 系统不健康（如果未来添加健康检查逻辑）
    """
    try:
        # 检查数据库连接
        stats = document_store.get_stats()
        
        return {
            "status": "healthy",
            "version": "0.2.0",
            "timestamp": time.time(),
            "database": "connected",
            "documents": stats.get('total_documents', 0)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "version": "0.2.0",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.post("/api/cache/clear", tags=["System"])
async def clear_cache(doc_id: Optional[str] = None):
    """
    清除缓存
    
    清除解析器缓存，可用于释放内存或强制重新加载解析器。
    
    **参数**:
    - `doc_id`: 可选的文档ID，如果提供则只清除该文档的缓存，否则清除所有缓存
    
    **返回**:
    - `message`: 操作结果消息
    - `cleared_count`: 清除的缓存项数量
    
    **示例**:
    ```bash
    # 清除所有缓存
    curl -X POST "http://localhost:8090/api/cache/clear"
    
    # 清除特定文档的缓存
    curl -X POST "http://localhost:8090/api/cache/clear?doc_id=abc12345"
    ```
    """
    try:
        if doc_id:
            # 验证文档ID格式
            from .utils import validate_doc_id
            if not validate_doc_id(doc_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document ID format: {doc_id}"
                )
            
            # 获取清除前的缓存大小
            cache_stats_before = query_service.get_cache_stats()
            before_count = cache_stats_before['size']
            
            # 清除指定文档的缓存
            query_service.clear_parser_cache(doc_id)
            
            # 获取清除后的缓存大小
            cache_stats_after = query_service.get_cache_stats()
            after_count = cache_stats_after['size']
            
            cleared_count = before_count - after_count
            
            return {
                "message": f"Cache cleared for document {doc_id}",
                "doc_id": doc_id,
                "cleared_count": cleared_count
            }
        else:
            # 获取清除前的缓存大小
            cache_stats_before = query_service.get_cache_stats()
            before_count = cache_stats_before['size']
            
            # 清除所有缓存
            query_service.clear_parser_cache()
            
            return {
                "message": "All cache cleared",
                "cleared_count": before_count
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/stats", tags=["System"])
async def get_cache_stats():
    """
    获取缓存统计信息
    
    返回当前缓存的使用情况。
    
    **返回**:
    - `size`: 当前缓存项数量
    - `max_size`: 最大缓存项数量
    - `keys`: 缓存键列表（仅前10个，避免响应过大）
    """
    try:
        stats = query_service.get_cache_stats()
        # 限制返回的键数量，避免响应过大
        keys = stats.get('keys', [])[:10]
        
        return {
            "size": stats['size'],
            "max_size": stats['max_size'],
            "keys": keys,
            "keys_total": len(stats.get('keys', []))
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics", tags=["System"])
async def get_metrics():
    """
    获取系统指标（基础监控）
    
    返回系统的基本统计信息，可用于监控和健康检查。
    
    **返回字段**:
    - `documents`: 文档统计
      - `total`: 总文档数
      - `ready`: 就绪文档数
      - `parsing`: 正在解析的文档数
      - `error`: 错误文档数
      - `pending`: 等待解析的文档数
    - `conversations`: 对话统计
      - `total`: 总对话数
    - `messages`: 消息统计
      - `total`: 总消息数
    - `system`: 系统信息
      - `status`: 系统状态
      - `version`: 系统版本
      - `timestamp`: 时间戳
    - `cache`: 缓存统计
      - `parser_cache_size`: 解析器缓存大小
      - `parser_cache_max`: 解析器缓存最大值
    """
    try:
        stats = document_store.get_stats()
        
        # 获取解析中的文档数量
        all_docs = document_store.get_all_documents()
        status_counts = {}
        for doc in all_docs:
            status = doc.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 获取缓存统计
        parser_cache_info = query_service._parser_cache
        parser_cache_size = len(parser_cache_info)
        parser_cache_max = query_service._max_cache_size
        
        return {
            "documents": {
                "total": stats['total_documents'],
                "ready": stats['ready_documents'],
                "parsing": status_counts.get('parsing', 0) + 
                          status_counts.get('parsing_mineru', 0) +
                          status_counts.get('parsing_markdown', 0) +
                          status_counts.get('adding_locations', 0),
                "error": status_counts.get('error', 0),
                "pending": status_counts.get('pending', 0),
            },
            "conversations": {
                "total": stats['total_conversations'],
            },
            "messages": {
                "total": stats['total_messages'],
            },
            "system": {
                "status": "healthy",
                "version": "0.2.0",
                "timestamp": time.time(),
            },
            "cache": {
                "parser_cache_size": parser_cache_size,
                "parser_cache_max": parser_cache_max,
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 主入口 =============

def main():
    """启动服务"""
    import uvicorn

    host = get_config_value('api', 'host', '0.0.0.0')
    port = get_config_value('api', 'port', 8090)

    print(f"Starting OpenIndex server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
