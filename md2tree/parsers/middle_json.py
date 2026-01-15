"""
Middle JSON Parser

解析 MinerU 的 middle.json 文件，提供精确的 PDF 坐标和块级别的定位功能。
middle.json 包含最精确的坐标信息，直接使用 PDF 坐标系。
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

from .base import BaseParser, SearchResult, LocationInfo, HeaderInfo

logger = logging.getLogger(__name__)


@dataclass
class TextSpan:
    """文本片段"""
    bbox: List[float]          # [x1, y1, x2, y2] PDF 坐标
    type: str                  # text, inline_equation 等
    content: str               # 文本内容


@dataclass
class TextLine:
    """文本行"""
    bbox: List[float]          # [x1, y1, x2, y2] PDF 坐标
    spans: List[TextSpan]      # 文本片段列表


@dataclass
class ParaBlock:
    """段落块"""
    bbox: List[float]          # [x1, y1, x2, y2] PDF 坐标
    type: str                  # title, text, image, table 等
    angle: float               # 旋转角度
    lines: List[TextLine]      # 行列表
    index: int                 # 块索引
    page_idx: int = field(default=0)  # 页码


@dataclass
class PageInfo:
    """页面信息"""
    page_idx: int
    page_size: Tuple[int, int]  # [width, height]
    para_blocks: List[ParaBlock]
    discarded_blocks: List[ParaBlock]


class MiddleJSONParser(BaseParser):
    """Middle JSON 解析器 - 提供精确的 PDF 坐标"""

    def __init__(self, middle_json_path: str):
        """
        初始化解析器

        Args:
            middle_json_path: middle.json 文件路径
        """
        self.middle_json_path = Path(middle_json_path)
        self.pages: List[PageInfo] = []
        self._load_middle_json()

        # 构建文本到块的映射
        self._build_text_to_block_mapping()

        # 构建块索引
        self._build_block_index()

    def _load_middle_json(self) -> None:
        """加载 middle.json 文件"""
        with open(self.middle_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pdf_info = data.get('pdf_info', [])

        for page_data in pdf_info:
            page_idx = page_data.get('page_idx', 0)
            page_size = tuple(page_data.get('page_size', [612, 792]))

            # 解析 para_blocks
            para_blocks = []
            for block_data in page_data.get('para_blocks', []):
                block = self._parse_para_block(block_data, page_idx)
                if block:
                    para_blocks.append(block)

            # 解析 discarded_blocks
            discarded_blocks = []
            for block_data in page_data.get('discarded_blocks', []):
                block = self._parse_para_block(block_data, page_idx)
                if block:
                    discarded_blocks.append(block)

            page = PageInfo(
                page_idx=page_idx,
                page_size=page_size,
                para_blocks=para_blocks,
                discarded_blocks=discarded_blocks
            )
            self.pages.append(page)

        logger.info(f"Loaded {len(self.pages)} pages from {self.middle_json_path}")
        total_para = sum(len(p.para_blocks) for p in self.pages)
        total_discarded = sum(len(p.discarded_blocks) for p in self.pages)
        logger.debug(f"  Total para_blocks: {total_para}")
        logger.debug(f"  Total discarded_blocks: {total_discarded}")

    def _parse_para_block(self, block_data: Dict[str, Any], page_idx: int) -> Optional[ParaBlock]:
        """解析段落块"""
        bbox = block_data.get('bbox', [0, 0, 0, 0])
        block_type = block_data.get('type', 'text')
        angle = block_data.get('angle', 0)
        index = block_data.get('index', 0)

        # 解析 lines
        lines = []
        for line_data in block_data.get('lines', []):
            line_bbox = line_data.get('bbox', [0, 0, 0, 0])

            # 解析 spans
            spans = []
            for span_data in line_data.get('spans', []):
                span = TextSpan(
                    bbox=span_data.get('bbox', [0, 0, 0, 0]),
                    type=span_data.get('type', 'text'),
                    content=span_data.get('content', '')
                )
                spans.append(span)

            line = TextLine(bbox=line_bbox, spans=spans)
            lines.append(line)

        return ParaBlock(
            bbox=bbox,
            type=block_type,
            angle=angle,
            lines=lines,
            index=index,
            page_idx=page_idx
        )

    def _build_text_to_block_mapping(self) -> None:
        """构建文本到块的映射，用于快速查找"""
        self.text_to_blocks: Dict[str, List[ParaBlock]] = {}

        for page in self.pages:
            for block in page.para_blocks:
                # 获取块的完整文本
                block_text = self._get_block_text(block)
                if block_text:
                    if block_text not in self.text_to_blocks:
                        self.text_to_blocks[block_text] = []
                    self.text_to_blocks[block_text].append(block)

    def _build_block_index(self) -> None:
        """构建块索引，按页码和类型组织"""
        self.blocks_by_page: Dict[int, List[ParaBlock]] = {}
        self.blocks_by_type: Dict[str, List[ParaBlock]] = {}
        self.title_blocks: List[ParaBlock] = []

        for page in self.pages:
            page_idx = page.page_idx
            self.blocks_by_page[page_idx] = []

            for block in page.para_blocks:
                # 按页索引
                self.blocks_by_page[page_idx].append(block)

                # 按类型索引
                block_type = block.type
                if block_type not in self.blocks_by_type:
                    self.blocks_by_type[block_type] = []
                self.blocks_by_type[block_type].append(block)

                # 标题索引
                if block_type == 'title':
                    self.title_blocks.append(block)

    def _get_block_text(self, block: ParaBlock) -> str:
        """获取块的完整文本"""
        text_parts = []
        for line in block.lines:
            for span in line.spans:
                text_parts.append(span.content)
        return ''.join(text_parts).strip()

    # ============= BaseParser 接口实现 =============

    def search(self, query: str, fuzzy: bool = True) -> List[SearchResult]:
        """
        搜索文本（实现 BaseParser 接口）
        
        Args:
            query: 搜索关键词
            fuzzy: 是否模糊匹配
            
        Returns:
            搜索结果列表
        """
        results = []
        for page in self.pages:
            page_size = page.page_size
            for block in page.para_blocks:
                block_text = self._get_block_text(block)
                
                match = False
                if fuzzy:
                    match = query.lower() in block_text.lower()
                else:
                    match = query in block_text
                
                if match:
                    results.append(SearchResult(
                        page_idx=block.page_idx,
                        bbox=block.bbox,
                        text=block_text,
                        type=block.type,
                        context=block_text[:150],
                        pdf_bbox=block.bbox  # middle.json 直接使用 PDF 坐标
                    ))
        
        return results

    def get_location(self, title: str, text: str = "") -> Optional[LocationInfo]:
        """
        获取节点位置信息（实现 BaseParser 接口）
        
        Args:
            title: 节点标题
            text: 节点文本内容
            
        Returns:
            位置信息
        """
        # 首先在标题块中查找
        title_block = self.find_title_by_text(title)
        if title_block:
            page_size = self.get_page_size(title_block.page_idx)
            return LocationInfo(
                page_idx=title_block.page_idx,
                bbox=title_block.bbox,
                type=title_block.type,
                text=self._get_block_text(title_block),
                page_size=list(page_size) if page_size else None
            )
        
        # 如果没找到标题，在所有块中模糊查找
        blocks = self.find_blocks_by_text(title, fuzzy=True)
        if blocks:
            block = blocks[0]
            page_size = self.get_page_size(block.page_idx)
            return LocationInfo(
                page_idx=block.page_idx,
                bbox=block.bbox,
                type=block.type,
                text=self._get_block_text(block),
                page_size=list(page_size) if page_size else None
            )
        
        return None

    def get_headers(self) -> List[HeaderInfo]:
        """获取所有标题（实现 BaseParser 接口）"""
        headers = []
        for block in self.title_blocks:
            headers.append(HeaderInfo(
                text=self._get_block_text(block),
                level=1,  # middle.json 不区分标题级别
                page_idx=block.page_idx,
                bbox=block.bbox,
                type=block.type
            ))
        return headers

    def get_total_pages(self) -> int:
        """获取总页数（实现 BaseParser 接口）"""
        return len(self.pages)

    # ============= 原有方法 =============

    def get_page_size(self, page_idx: int) -> Optional[Tuple[int, int]]:
        """获取页面尺寸"""
        if 0 <= page_idx < len(self.pages):
            return self.pages[page_idx].page_size
        return None

    def get_blocks_by_page(self, page_idx: int) -> List[ParaBlock]:
        """获取指定页的所有块"""
        return self.blocks_by_page.get(page_idx, [])

    def get_blocks_by_type(self, block_type: str) -> List[ParaBlock]:
        """获取指定类型的所有块"""
        return self.blocks_by_type.get(block_type, [])

    def get_titles(self) -> List[ParaBlock]:
        """获取所有标题块"""
        return self.title_blocks

    def find_blocks_by_text(self, search_text: str, fuzzy: bool = False) -> List[ParaBlock]:
        """
        查找包含指定文本的块

        Args:
            search_text: 要查找的文本
            fuzzy: 是否模糊匹配

        Returns:
            匹配的块列表
        """
        results = []

        for page in self.pages:
            for block in page.para_blocks:
                block_text = self._get_block_text(block)

                if fuzzy:
                    if search_text.lower() in block_text.lower():
                        results.append(block)
                else:
                    if search_text in block_text:
                        results.append(block)

        return results

    def find_title_by_text(self, title_text: str) -> Optional[ParaBlock]:
        """
        查找标题块

        Args:
            title_text: 标题文本

        Returns:
            匹配的标题块，如果没有找到返回 None
        """
        for title_block in self.title_blocks:
            block_text = self._get_block_text(title_block)
            if title_text in block_text or block_text in title_text:
                return title_block
        return None

    def get_blocks_in_bbox(
        self,
        page_idx: int,
        bbox: List[float],
        tolerance: float = 0
    ) -> List[ParaBlock]:
        """
        获取指定 bbox 范围内的块

        Args:
            page_idx: 页码
            bbox: 边界框 [x1, y1, x2, y2]
            tolerance: 容差（像素）

        Returns:
            在范围内的块列表
        """
        x1, y1, x2, y2 = bbox
        results = []

        for block in self.get_blocks_by_page(page_idx):
            bx1, by1, bx2, by2 = block.bbox

            # 检查是否在范围内（允许容差）
            if (bx1 >= x1 - tolerance and bx2 <= x2 + tolerance and
                by1 >= y1 - tolerance and by2 <= y2 + tolerance):
                results.append(block)

        return results

    def get_block_location_info(self, block: ParaBlock) -> Dict[str, Any]:
        """
        获取块的详细位置信息

        Args:
            block: 段落块

        Returns:
            位置信息字典
        """
        return {
            'page_idx': block.page_idx,
            'bbox': block.bbox,
            'type': block.type,
            'text': self._get_block_text(block),
            'line_count': len(block.lines),
            'page_size': self.get_page_size(block.page_idx),
            'spans': [
                {
                    'text': span.content,
                    'bbox': span.bbox,
                    'type': span.type
                }
                for line in block.lines
                for span in line.spans
            ]
        }

    def locate_node_in_tree(
        self,
        node_title: str,
        node_text: str
    ) -> Dict[str, Any]:
        """
        定位树节点在 PDF 中的位置

        Args:
            node_title: 节点标题
            node_text: 节点文本

        Returns:
            位置信息，包含标题块和内容块
        """
        # 查找标题块
        title_block = self.find_title_by_text(node_title)

        result = {
            'title_block': None,
            'content_blocks': [],
            'page_range': (None, None),
            'all_blocks': []
        }

        if title_block:
            result['title_block'] = self.get_block_location_info(title_block)
            start_page = title_block.page_idx

            # 查找标题后的内容块
            found_title = False
            page_indices = set()
            page_indices.add(start_page)

            for page in self.pages:
                if page.page_idx < start_page:
                    continue

                for block in page.para_blocks:
                    # 跳过标题之前的块
                    if not found_title:
                        if block == title_block:
                            found_title = True
                        continue

                    # 遇到下一个标题时停止
                    if block.type == 'title' and block.index > title_block.index:
                        # 检查标题级别
                        block_text = self._get_block_text(block)
                        # 简单判断：如果标题更短或更高级，停止
                        if len(block_text) < 20 or block.index <= title_block.index + 5:
                            break

                    # 添加内容块
                    result['content_blocks'].append(self.get_block_location_info(block))
                    result['all_blocks'].append(self.get_block_location_info(block))
                    page_indices.add(block.page_idx)

            result['page_range'] = (
                min(page_indices) if page_indices else None,
                max(page_indices) if page_indices else None
            )

        return result

    def search_and_locate(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索文本并返回位置信息（支持关键词搜索）

        Args:
            query: 搜索查询（可以是自然语言问题或关键词）

        Returns:
            匹配结果列表，包含位置信息
        """
        # 提取关键词：移除常见停用词，保留有意义的词
        stop_words = {
            'what', 'is', 'are', 'the', 'a', 'an', 'of', 'in', 'to', 'for',
            'and', 'or', 'how', 'why', 'when', 'where', 'which', 'who',
            'this', 'that', 'these', 'those', 'it', 'its', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'about',
            '是', '的', '了', '和', '与', '在', '什么', '怎么', '如何',
            '为什么', '哪些', '这个', '那个', '一个', '有', '吗', '呢'
        }

        # 分词并过滤
        words = query.lower().replace('?', '').replace('？', '').split()
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        # 如果没有提取到关键词，使用原始查询
        if not keywords:
            keywords = [query.lower()]

        # 对每个关键词搜索
        block_scores: Dict[int, Tuple[ParaBlock, int, str]] = {}  # block_id -> (block, score, matched_keyword)

        for keyword in keywords:
            blocks = self.find_blocks_by_text(keyword, fuzzy=True)
            for block in blocks:
                block_id = id(block)
                if block_id in block_scores:
                    # 增加分数（多个关键词匹配）
                    old_block, old_score, old_kw = block_scores[block_id]
                    block_scores[block_id] = (old_block, old_score + 1, f"{old_kw}, {keyword}")
                else:
                    block_scores[block_id] = (block, 1, keyword)

        # 按分数排序
        sorted_blocks = sorted(block_scores.values(), key=lambda x: x[1], reverse=True)

        results = []
        for block, score, matched_kw in sorted_blocks:
            info = self.get_block_location_info(block)
            block_text = info['text']

            # 找到第一个匹配关键词的位置来提取上下文
            first_kw = matched_kw.split(',')[0].strip()
            start_idx = block_text.lower().find(first_kw)
            if start_idx < 0:
                start_idx = 0

            # 获取周围上下文
            context_start = max(0, start_idx - 30)
            context_end = min(len(block_text), start_idx + 120)
            context = block_text[context_start:context_end]
            if context_start > 0:
                context = '...' + context
            if context_end < len(block_text):
                context = context + '...'

            results.append({
                'page_idx': block.page_idx,
                'bbox': block.bbox,
                'type': block.type,
                'context': context,
                'match_position': start_idx,
                'matched_keywords': matched_kw,
                'score': score,
                'full_info': info
            })

        return results


def add_middlejson_location_to_tree(
    tree_structure: List[Dict[str, Any]],
    middle_json_path: str
) -> List[Dict[str, Any]]:
    """
    使用 middle.json 为树结构添加精确的位置信息

    Args:
        tree_structure: md2tree 生成的树结构
        middle_json_path: middle.json 文件路径

    Returns:
        增强后的树结构
    """
    parser = MiddleJSONParser(middle_json_path)

    def add_location_to_node(node: Dict[str, Any]) -> Dict[str, Any]:
        """递归地为节点添加位置信息"""
        title = node.get('title', '')
        text = node.get('text', '')

        # 使用 middle.json 定位
        location_info = parser.locate_node_in_tree(title, text)

        result = node.copy()
        result['page_info'] = {
            'page_range': location_info['page_range'],
            'title_block': location_info['title_block'],
            'content_blocks': location_info['content_blocks'],
            'total_blocks': len(location_info['all_blocks'])
        }

        # 递归处理子节点
        if node.get('nodes'):
            result['nodes'] = [add_location_to_node(n) for n in node['nodes']]

        return result

    return [add_location_to_node(node) for node in tree_structure]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python middle_json_parser.py <middle.json>")
        sys.exit(1)

    middle_json_path = sys.argv[1]

    parser = MiddleJSONParser(middle_json_path)

    print("\n=== 标题块 ===")
    for title in parser.get_titles():
        text = parser._get_block_text(title)
        print(f"[Page {title.page_idx + 1}] {text}")
        print(f"  bbox: {title.bbox}")
        print(f"  type: {title.type}")

    # 测试搜索
    if len(sys.argv) > 2:
        query = sys.argv[2]
        print(f"\n=== 搜索 '{query}' ===")
        results = parser.search_and_locate(query)
        for result in results:
            print(f"[Page {result['page_idx'] + 1}] {result['type']}")
            print(f"  bbox: {result['bbox']}")
            print(f"  context: {result['context'][:100]}...")
