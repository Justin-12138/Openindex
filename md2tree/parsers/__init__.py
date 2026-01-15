"""
解析器模块

提供 PDF 解析和位置信息提取的统一接口。
"""

from .base import BaseParser, SearchResult, LocationInfo
from .mineru import MinerUParser
from .middle_json import MiddleJSONParser

__all__ = [
    'BaseParser',
    'SearchResult',
    'LocationInfo',
    'MinerUParser',
    'MiddleJSONParser',
]
