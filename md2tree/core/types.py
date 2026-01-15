"""
类型定义模块

定义项目中使用的类型别名和 TypedDict，提供更好的类型提示支持。
"""

from typing import TypedDict, List, Dict, Any, Optional, Union
from dataclasses import dataclass, field


# =============================================================================
# 树结构类型
# =============================================================================

class PageInfoBlock(TypedDict, total=False):
    """页面信息块"""
    page_idx: int
    bbox: List[float]
    type: str
    text: str
    page_size: List[float]
    spans: List[Dict[str, Any]]


class PageInfo(TypedDict, total=False):
    """节点的页面位置信息"""
    page_range: List[int]
    title_block: PageInfoBlock
    content_blocks: List[PageInfoBlock]


class TreeNode(TypedDict, total=False):
    """树节点"""
    title: str
    node_id: str
    text: str
    level: int
    line_num: int
    nodes: List['TreeNode']
    summary: Optional[str]
    page_info: Optional[PageInfo]
    token_count: Optional[int]


class TreeStructure(TypedDict):
    """完整的树结构"""
    doc_name: str
    doc_description: Optional[str]
    structure: List[TreeNode]


# =============================================================================
# 搜索结果类型
# =============================================================================

class SearchResultDict(TypedDict, total=False):
    """搜索结果字典"""
    page_idx: int
    bbox: List[float]
    text: str
    type: str
    context: str
    score: float
    pdf_bbox: Optional[List[float]]


class LocationInfoDict(TypedDict, total=False):
    """位置信息字典"""
    page_idx: int
    bbox: List[float]
    type: str
    text: str
    page_size: Optional[List[float]]
    spans: List[Dict[str, Any]]


# =============================================================================
# API 请求/响应类型
# =============================================================================

class QueryRequestDict(TypedDict, total=False):
    """查询请求"""
    doc_id: str
    query: str
    top_k: int
    conversation_id: Optional[str]


class SelectedNodeDict(TypedDict):
    """选中的节点"""
    node_id: str
    title: str
    relevance: float
    reason: str


class SourceDict(TypedDict, total=False):
    """引用来源"""
    node_id: str
    title: str
    text: str
    page_range: Optional[List[int]]


class QueryResponseDict(TypedDict):
    """查询响应"""
    answer: str
    selected_nodes: List[SelectedNodeDict]
    sources: List[SourceDict]
    locations: List[LocationInfoDict]


# =============================================================================
# 文档类型
# =============================================================================

class DocumentDict(TypedDict, total=False):
    """文档信息"""
    id: str
    name: str
    original_filename: str
    pdf_path: Optional[str]
    md_path: Optional[str]
    tree_path: Optional[str]
    mineru_dir: Optional[str]
    status: str
    total_nodes: Optional[int]
    max_depth: Optional[int]
    total_pages: Optional[int]
    file_size: int
    created_at: str
    updated_at: str
    parsed_at: Optional[str]
    error_message: Optional[str]


class ConversationDict(TypedDict, total=False):
    """对话信息"""
    id: str
    doc_id: str
    title: str
    created_at: str
    updated_at: str
    deleted_at: Optional[str]
    messages: List['MessageDict']


class MessageDict(TypedDict, total=False):
    """消息信息"""
    id: int
    conversation_id: str
    role: str
    content: str
    created_at: str
    references: Optional[List[Dict[str, Any]]]
    selected_nodes: Optional[List[Dict[str, Any]]]
    locations: Optional[List[Dict[str, Any]]]


# =============================================================================
# 配置类型
# =============================================================================

class LLMConfigDict(TypedDict, total=False):
    """LLM 配置"""
    api_key: str
    api_base: str
    model: str
    temperature: float
    max_concurrent_requests: int
    request_timeout: int
    max_retries: int
    retry_delay: float


class MineruConfigDict(TypedDict, total=False):
    """MinerU 配置"""
    server_url: str
    api_url: str
    backend: str
    output_dir: str
    executable: str
    extra_args: List[str]


class AppConfigDict(TypedDict, total=False):
    """应用配置"""
    upload_dir: str
    max_file_size: int
    allowed_extensions: List[str]
    max_message_length: int


class ConfigDict(TypedDict, total=False):
    """完整配置"""
    llm: LLMConfigDict
    mineru: MineruConfigDict
    app: AppConfigDict
    api: Dict[str, Any]
    thinning: Dict[str, Any]
    summary: Dict[str, Any]
    output: Dict[str, Any]


# =============================================================================
# 数据类（用于运行时）
# =============================================================================

@dataclass
class TreeStats:
    """树结构统计信息"""
    total_nodes: int = 0
    max_depth: int = 0
    total_tokens: int = 0
    nodes_by_level: Dict[int, int] = field(default_factory=dict)


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    doc_id: str
    tree_path: Optional[str] = None
    mineru_dir: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


# =============================================================================
# 类型别名
# =============================================================================

# 边界框类型 [x1, y1, x2, y2]
BBox = List[float]

# 页面尺寸 [width, height]
PageSize = List[float]

# 节点 ID
NodeId = str

# 文档 ID
DocId = str

# JSON 兼容类型
JsonValue = Union[str, int, float, bool, None, List['JsonValue'], Dict[str, 'JsonValue']]
JsonDict = Dict[str, Any]
