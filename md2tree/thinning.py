"""
树剪枝模块（兼容导入）

此文件保持向后兼容，实际实现已移动到 llm/thinning.py
"""

# 从新位置重新导出所有内容
from .llm.thinning import (
    apply_thinning,
    update_node_token_counts,
    thin_tree_by_token_count,
)

__all__ = [
    'apply_thinning',
    'update_node_token_counts',
    'thin_tree_by_token_count',
]
