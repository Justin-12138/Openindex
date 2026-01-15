"""
PDF 处理模块

提供 PDF 坐标转换和查看功能。
"""

from .coordinates import CoordinateTransform
from .viewer import PDFHighlighter, PDFLocationViewer, create_retrieval_result_html

# 别名（向后兼容）
CoordinateTransformer = CoordinateTransform
PDFViewer = PDFHighlighter

__all__ = [
    # 实际类名
    'CoordinateTransform',
    'PDFHighlighter',
    'PDFLocationViewer',
    'create_retrieval_result_html',
    # 向后兼容的别名
    'CoordinateTransformer',
    'PDFViewer',
]
