"""
核心功能模块

提供 Markdown 到树结构的转换、配置管理和工具函数。
"""

from .config import (
    load_config,
    get_config_value,
    reload_config,
    get_default_config,
    validate_config,
    get_env_value,
)

from .constants import (
    # PDF 常量
    PDF_DEFAULT_WIDTH,
    PDF_DEFAULT_HEIGHT,
    MINERU_INTERNAL_WIDTH,
    MINERU_INTERNAL_HEIGHT,
    # 树处理常量
    DEFAULT_TOKEN_THRESHOLD,
    DEFAULT_SUMMARY_THRESHOLD,
    DEFAULT_MAX_DEPTH,
    # API 常量
    DEFAULT_TOP_K,
    DEFAULT_MAX_HISTORY,
    DEFAULT_API_PORT,
    # 文件常量
    DEFAULT_MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS,
    DEFAULT_MAX_MESSAGE_LENGTH,
    # LLM 常量
    DEFAULT_MAX_CONCURRENT_REQUESTS,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TEMPERATURE,
    DEFAULT_LLM_MODEL,
    # 状态类
    DocumentStatus,
    ParseJobStatus,
    MessageRole,
)

from .converter import (
    md_to_tree,
    md_to_tree_async,
    save_tree,
    extract_headers,
    extract_node_content,
    build_tree,
    format_structure,
    print_toc,
)

from .tree import (
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

from .context import (
    AppContext,
    get_context,
    get_or_create_context,
    set_context,
    reset_context,
    ContextManager,
    AsyncContextManager,
    create_context_with_config,
    get_semaphore_from_context,
    get_config_from_context,
    with_context,
    with_context_async,
)

__all__ = [
    # 配置
    'load_config',
    'get_config_value',
    'reload_config',
    'get_default_config',
    'validate_config',
    'get_env_value',
    # 转换器
    'md_to_tree',
    'md_to_tree_async',
    'save_tree',
    'extract_headers',
    'extract_node_content',
    'build_tree',
    'format_structure',
    'print_toc',
    # 树操作
    'structure_to_list',
    'get_leaf_nodes',
    'find_node_by_id',
    'find_node_by_title',
    'remove_field',
    'get_tree_stats',
    'validate_tree',
    'sanitize_filename',
    'pretty_print_tree',
    # 常量
    'PDF_DEFAULT_WIDTH',
    'PDF_DEFAULT_HEIGHT',
    'MINERU_INTERNAL_WIDTH',
    'MINERU_INTERNAL_HEIGHT',
    'DEFAULT_TOKEN_THRESHOLD',
    'DEFAULT_SUMMARY_THRESHOLD',
    'DEFAULT_MAX_DEPTH',
    'DEFAULT_TOP_K',
    'DEFAULT_MAX_HISTORY',
    'DEFAULT_API_PORT',
    'DEFAULT_MAX_FILE_SIZE',
    'ALLOWED_EXTENSIONS',
    'DEFAULT_MAX_MESSAGE_LENGTH',
    'DEFAULT_MAX_CONCURRENT_REQUESTS',
    'DEFAULT_REQUEST_TIMEOUT',
    'DEFAULT_MAX_RETRIES',
    'DEFAULT_TEMPERATURE',
    'DEFAULT_LLM_MODEL',
    'DocumentStatus',
    'ParseJobStatus',
    'MessageRole',
    # 上下文管理
    'AppContext',
    'get_context',
    'get_or_create_context',
    'set_context',
    'reset_context',
    'ContextManager',
    'AsyncContextManager',
    'create_context_with_config',
    'get_semaphore_from_context',
    'get_config_from_context',
    'with_context',
    'with_context_async',
]
