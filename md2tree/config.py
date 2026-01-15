"""
配置管理模块（兼容导入）

此文件保持向后兼容，实际实现已移动到 core/config.py
"""

# 从新位置重新导出所有内容
from .core.config import (
    load_config,
    get_config_value,
    reload_config,
    get_default_config,
    validate_config,
    get_env_value,
)

__all__ = [
    'load_config',
    'get_config_value',
    'reload_config',
    'get_default_config',
    'validate_config',
    'get_env_value',
]
