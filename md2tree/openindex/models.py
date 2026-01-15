"""
数据模型定义
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"              # 等待解析
    PARSING = "parsing"              # 正在解析（通用状态）
    PARSING_MINERU = "parsing_mineru"      # 正在调用 MinerU
    PARSING_MARKDOWN = "parsing_markdown"  # 正在转换 Markdown
    ADDING_LOCATIONS = "adding_locations"  # 正在添加位置信息
    GENERATING_SUMMARY = "generating_summary"  # 正在生成摘要（如果启用）
    READY = "ready"                  # 解析完成
    ERROR = "error"                  # 解析失败


class BBox(BaseModel):
    """边界框"""
    x1: float
    y1: float
    x2: float
    y2: float


class BlockLocation(BaseModel):
    """块位置信息"""
    page_idx: int
    page_num: int  # 1-based
    bbox: List[float]
    type: str


class TreeNode(BaseModel):
    """树节点"""
    title: str
    node_id: Optional[str] = None
    text: Optional[str] = None
    summary: Optional[str] = None
    line_num: Optional[int] = None
    page_info: Optional[Dict[str, Any]] = None
    nodes: List["TreeNode"] = []


class Document(BaseModel):
    """文档信息"""
    id: str
    name: str
    pdf_path: str
    status: DocumentStatus = DocumentStatus.PENDING
    tree_structure: Optional[List[TreeNode]] = None
    stats: Optional[Dict[str, int]] = None
    created_at: Optional[str] = None
    mineru_dir: Optional[str] = None


class UploadResponse(BaseModel):
    """上传响应"""
    doc_id: str
    name: str
    status: DocumentStatus
    message: str


class ParseRequest(BaseModel):
    """解析请求"""
    doc_id: str


class QueryRequest(BaseModel):
    """查询请求"""
    doc_id: str
    query: str = Field(..., max_length=10000)  # 限制查询长度
    top_k: int = Field(default=5, ge=1, le=20)
    conversation_id: Optional[str] = None  # 可选的对话 ID，用于保存消息历史


class SelectedNode(BaseModel):
    """选中的节点"""
    node_id: str
    title: str
    relevance: float = 1.0
    reason: Optional[str] = None


class NodeLocation(BaseModel):
    """节点位置"""
    node_id: str
    title: str
    page_range: Optional[List[int]] = None
    title_block: Optional[BlockLocation] = None
    content_blocks: List[BlockLocation] = []


class QueryResponse(BaseModel):
    """查询响应"""
    query: str
    answer: str
    selected_nodes: List[SelectedNode]
    locations: List[NodeLocation]
    sources: List[Dict[str, Any]] = []


class SearchRequest(BaseModel):
    """搜索请求"""
    doc_id: str
    query: str
    max_results: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    """搜索结果"""
    rank: int
    page_num: int
    bbox: List[float]
    type: str
    context: str
    pdf_link: str


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    total_results: int
    results: List[SearchResult]


class TreeResponse(BaseModel):
    """树结构响应"""
    doc_id: str
    doc_name: str
    structure: List[TreeNode]
    stats: Dict[str, int]


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


class ConversationCreate(BaseModel):
    """创建对话请求"""
    doc_id: str
    title: Optional[str] = Field(default=None, max_length=100)


class MessageCreate(BaseModel):
    """创建消息请求"""
    conversation_id: str
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., max_length=50000)  # 限制消息长度 50000 字符


class ConversationResponse(BaseModel):
    """对话响应"""
    id: str
    doc_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Dict[str, Any]] = []


# 允许 TreeNode 自引用
TreeNode.model_rebuild()
