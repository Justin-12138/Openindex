"""
LLM API 模块（兼容导入）

此文件保持向后兼容，实际实现已移动到 llm/client.py
"""

# 从新位置重新导出所有内容
from .llm.client import (
    LLMConfig,
    call_llm,
    call_llm_async,
    call_llm_async_batch,
    count_tokens,
    reset_semaphore,
    get_semaphore,
    reload_config,
)

# 兼容旧的配置函数导入
from .core.config import (
    load_config,
    get_config_value,
    get_default_config,
)

__all__ = [
    'LLMConfig',
    'call_llm',
    'call_llm_async',
    'call_llm_async_batch',
    'count_tokens',
    'reset_semaphore',
    'get_semaphore',
    'reload_config',
    'load_config',
    'get_config_value',
    'get_default_config',
]
