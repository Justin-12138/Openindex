"""
工作流模块（兼容导入）

此文件保持向后兼容，实际实现已移动到 core/workflow.py
"""

# 从新位置重新导出所有内容
from .core.workflow import (
    PDFToTreeWorkflow,
    run_workflow,
    run_workflow_async,
)

__all__ = [
    'PDFToTreeWorkflow',
    'run_workflow',
    'run_workflow_async',
]
