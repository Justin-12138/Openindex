"""
Markdown to Tree 转换模块（兼容导入）

此文件保持向后兼容，实际实现已移动到 core/converter.py
"""

# 从新位置重新导出所有内容
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

__all__ = [
    'md_to_tree',
    'md_to_tree_async',
    'save_tree',
    'extract_headers',
    'extract_node_content',
    'build_tree',
    'format_structure',
    'print_toc',
]
