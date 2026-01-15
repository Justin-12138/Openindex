"""
md2tree - A simple Markdown to Tree converter

This package converts Markdown files into hierarchical tree structures
based on the header hierarchy, with optional LLM-powered summarization
and PDF location integration.

项目结构:
    md2tree/
    ├── __init__.py          # 包初始化
    ├── config.toml          # 配置文件
    │
    ├── core/                # 核心功能
    │   ├── config.py        # 配置管理
    │   ├── converter.py     # 转换逻辑（md_to_tree）
    │   ├── tree.py          # 树操作工具
    │   └── workflow.py      # 工作流整合
    │
    ├── llm/                 # LLM 集成
    │   ├── client.py        # LLM API 客户端
    │   ├── summary.py       # 摘要生成
    │   └── thinning.py      # 树剪枝
    │
    ├── parsers/             # 解析器
    │   ├── base.py          # 解析器基类
    │   ├── mineru.py        # MinerU 解析器
    │   └── middle_json.py   # Middle JSON 解析器
    │
    ├── pdf/                 # PDF 处理
    │   ├── coordinates.py   # 坐标转换
    │   └── viewer.py        # PDF 查看器
    │
    ├── openindex/           # Web 应用
    │
    ├── examples/            # 示例代码
    │   ├── demo.py
    │   └── example.py
    │
    └── tests/               # 测试
"""

# ============= 核心模块 =============
# 配置管理
from .core.config import (
    load_config,
    get_config_value,
    reload_config,
    get_default_config,
    validate_config,
    setup_logging,
)

# 上下文管理
from .core.context import (
    AppContext,
    get_context,
    get_or_create_context,
    set_context,
    reset_context,
    create_context_with_config,
    get_semaphore_from_context,
    get_config_from_context,
)

# 常量
from .core.constants import (
    PDF_DEFAULT_WIDTH,
    PDF_DEFAULT_HEIGHT,
    MINERU_INTERNAL_WIDTH,
    MINERU_INTERNAL_HEIGHT,
    DEFAULT_TOKEN_THRESHOLD,
    DEFAULT_SUMMARY_THRESHOLD,
    DEFAULT_TOP_K,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_CONCURRENT_REQUESTS,
    DocumentStatus,
    ParseJobStatus,
    MessageRole,
)

# 类型定义
from .core.types import (
    TreeNode,
    TreeStructure,
    SearchResultDict,
    LocationInfoDict,
    DocumentDict,
    ConversationDict,
    MessageDict,
    TreeStats,
    ParseResult,
)

# 核心转换
from .core.converter import (
    md_to_tree,
    md_to_tree_async,
    save_tree,
    extract_headers,
    extract_node_content,
    build_tree,
    format_structure,
    print_toc,
)

# 树操作工具
from .core.tree import (
    structure_to_list,
    get_leaf_nodes,
    find_node_by_id,
    find_node_by_title,
    remove_field,
    get_tree_stats,
    validate_tree,
    sanitize_filename,
    pretty_print_tree,
)

# ============= LLM 模块 =============
from .llm.client import (
    LLMConfig,
    call_llm,
    call_llm_async,
    call_llm_async_batch,
    count_tokens,
    reset_semaphore,
)

from .llm.summary import (
    generate_node_summary,
    generate_summaries_for_structure,
    generate_doc_description,
    generate_doc_description_async,
)

from .llm.thinning import (
    apply_thinning,
    update_node_token_counts,
    thin_tree_by_token_count,
)

# ============= 解析器模块 =============
try:
    from .parsers import (
        BaseParser,
        SearchResult,
        LocationInfo,
        MinerUParser,
        MiddleJSONParser,
    )
    from .parsers.mineru import (
        ContentBlock,
        add_location_info_to_tree,
        create_pdf_link,
    )
    from .parsers.middle_json import (
        add_middlejson_location_to_tree,
    )
    _parsers_available = True
except ImportError:
    _parsers_available = False

# ============= PDF 模块 =============
try:
    from .pdf.viewer import (
        PDFHighlighter,
        PDFLocationViewer,
        create_retrieval_result_html,
    )
    _pdf_viewer_available = True
except ImportError:
    _pdf_viewer_available = False


__version__ = "2.5.0"
__all__ = [
    # 配置
    "load_config",
    "get_config_value",
    "reload_config",
    "get_default_config",
    "validate_config",
    # 上下文管理
    "AppContext",
    "get_context",
    "get_or_create_context",
    "set_context",
    "reset_context",
    "create_context_with_config",
    "get_semaphore_from_context",
    "get_config_from_context",
    # 常量
    "PDF_DEFAULT_WIDTH",
    "PDF_DEFAULT_HEIGHT",
    "MINERU_INTERNAL_WIDTH",
    "MINERU_INTERNAL_HEIGHT",
    "DEFAULT_TOKEN_THRESHOLD",
    "DEFAULT_SUMMARY_THRESHOLD",
    "DEFAULT_TOP_K",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_FILE_SIZE",
    "DEFAULT_MAX_CONCURRENT_REQUESTS",
    "DocumentStatus",
    "ParseJobStatus",
    "MessageRole",
    # 类型定义
    "TreeNode",
    "TreeStructure",
    "SearchResultDict",
    "LocationInfoDict",
    "DocumentDict",
    "ConversationDict",
    "MessageDict",
    "TreeStats",
    "ParseResult",
    # 核心转换
    "md_to_tree",
    "md_to_tree_async",
    "save_tree",
    "extract_headers",
    "extract_node_content",
    "build_tree",
    "format_structure",
    "print_toc",
    # 树操作
    "structure_to_list",
    "get_leaf_nodes",
    "find_node_by_id",
    "find_node_by_title",
    "remove_field",
    "get_tree_stats",
    "validate_tree",
    "sanitize_filename",
    "pretty_print_tree",
    # LLM
    "LLMConfig",
    "call_llm",
    "call_llm_async",
    "call_llm_async_batch",
    "count_tokens",
    "reset_semaphore",
    # 摘要
    "generate_node_summary",
    "generate_summaries_for_structure",
    "generate_doc_description",
    "generate_doc_description_async",
    # 树剪枝
    "apply_thinning",
    "update_node_token_counts",
    "thin_tree_by_token_count",
]

# 添加解析器导出
if _parsers_available:
    __all__.extend([
        "BaseParser",
        "SearchResult",
        "LocationInfo",
        "MinerUParser",
        "MiddleJSONParser",
        "ContentBlock",
        "add_location_info_to_tree",
        "create_pdf_link",
        "add_middlejson_location_to_tree",
    ])

# 添加 PDF 模块导出
if _pdf_viewer_available:
    __all__.extend([
        "PDFHighlighter",
        "PDFLocationViewer",
        "create_retrieval_result_html",
    ])
