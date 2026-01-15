"""
摘要生成模块（兼容导入）

此文件保持向后兼容，实际实现已移动到 llm/summary.py
"""

# 从新位置重新导出所有内容
from .llm.summary import (
    generate_node_summary,
    generate_summaries_for_structure,
    generate_doc_description,
    generate_doc_description_async,
)

__all__ = [
    'generate_node_summary',
    'generate_summaries_for_structure',
    'generate_doc_description',
    'generate_doc_description_async',
]
