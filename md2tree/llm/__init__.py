"""
LLM 集成模块

提供 LLM API 调用、摘要生成和树剪枝功能。
"""

from .client import (
    LLMConfig,
    call_llm,
    call_llm_async,
    call_llm_async_batch,
    count_tokens,
    reset_semaphore,
    get_semaphore,
)

# 为了向后兼容，从 core.config 重新导出配置函数
from ..core.config import (
    load_config,
    get_config_value,
    reload_config,
    get_default_config,
)

from .summary import (
    generate_node_summary,
    generate_summaries_for_structure,
    generate_doc_description,
    generate_doc_description_async,
)

from .thinning import (
    apply_thinning,
    update_node_token_counts,
    thin_tree_by_token_count,
)

__all__ = [
    # LLM 客户端
    'LLMConfig',
    'call_llm',
    'call_llm_async',
    'call_llm_async_batch',
    'count_tokens',
    'reset_semaphore',
    'get_semaphore',
    # 摘要生成
    'generate_node_summary',
    'generate_summaries_for_structure',
    'generate_doc_description',
    'generate_doc_description_async',
    # 树剪枝
    'apply_thinning',
    'update_node_token_counts',
    'thin_tree_by_token_count',
    # 配置（向后兼容）
    'load_config',
    'get_config_value',
    'reload_config',
    'get_default_config',
]
