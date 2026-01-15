"""
解析器抽象基类

定义所有解析器必须实现的统一接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SearchResult:
    """搜索结果"""
    page_idx: int               # 页码索引 (0-based)
    bbox: List[float]           # 边界框 [x1, y1, x2, y2]
    text: str                   # 匹配的文本
    type: str = "text"          # 块类型
    context: str = ""           # 上下文文本
    score: float = 1.0          # 相关性分数
    pdf_bbox: Optional[List[float]] = None  # PDF 坐标系下的边界框
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'page_idx': self.page_idx,
            'bbox': self.bbox,
            'text': self.text,
            'type': self.type,
            'context': self.context,
            'score': self.score,
            'pdf_bbox': self.pdf_bbox,
        }


@dataclass
class LocationInfo:
    """位置信息"""
    page_idx: int               # 页码索引 (0-based)
    bbox: List[float]           # 边界框 [x1, y1, x2, y2]
    type: str = "text"          # 块类型
    text: str = ""              # 文本内容
    page_size: Optional[List[float]] = None  # 页面尺寸 [width, height]
    spans: List[Dict] = field(default_factory=list)  # 文本 span 信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'page_idx': self.page_idx,
            'bbox': self.bbox,
            'type': self.type,
            'text': self.text,
        }
        if self.page_size:
            result['page_size'] = self.page_size
        if self.spans:
            result['spans'] = self.spans
        return result


@dataclass
class HeaderInfo:
    """标题信息"""
    text: str                   # 标题文本
    level: int                  # 标题级别 (1-6)
    page_idx: int               # 页码索引
    bbox: List[float]           # 边界框
    type: str = "title"         # 块类型


class BaseParser(ABC):
    """
    解析器抽象基类
    
    所有具体解析器（MinerUParser, MiddleJSONParser）都应继承此类。
    """
    
    @abstractmethod
    def search(self, query: str, fuzzy: bool = True) -> List[SearchResult]:
        """
        搜索文本
        
        Args:
            query: 搜索关键词
            fuzzy: 是否模糊匹配
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    def get_location(self, title: str, text: str = "") -> Optional[LocationInfo]:
        """
        获取节点位置信息
        
        Args:
            title: 节点标题
            text: 节点文本内容（可选）
            
        Returns:
            位置信息，如果未找到返回 None
        """
        pass
    
    @abstractmethod
    def get_headers(self) -> List[HeaderInfo]:
        """
        获取所有标题
        
        Returns:
            标题信息列表
        """
        pass
    
    @abstractmethod
    def get_total_pages(self) -> int:
        """
        获取总页数
        
        Returns:
            总页数
        """
        pass
    
    def search_and_locate(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索并返回位置信息（兼容旧接口）
        
        Args:
            query: 搜索关键词
            
        Returns:
            包含位置信息的字典列表
        """
        results = self.search(query)
        return [r.to_dict() for r in results]
    
    def find_text_location(self, text: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        查找文本位置（兼容旧接口）
        
        Args:
            text: 要查找的文本
            fuzzy: 是否模糊匹配
            
        Returns:
            位置信息字典列表
        """
        results = self.search(text, fuzzy=fuzzy)
        return [r.to_dict() for r in results]


def create_pdf_link(pdf_path: str, page_idx: int, bbox: List[float] = None) -> str:
    """
    创建 PDF 链接
    
    Args:
        pdf_path: PDF 文件路径
        page_idx: 页码索引 (0-based)
        bbox: 可选的边界框
        
    Returns:
        PDF 链接字符串
    """
    link = f"{pdf_path}#page={page_idx + 1}"
    if bbox:
        # 添加高亮区域参数（如果 PDF 阅读器支持）
        link += f"&view=FitH&highlight={','.join(str(int(x)) for x in bbox)}"
    return link
