"""
MinerU Result Parser

解析 MinerU 的输出结果，将 page_idx 和 bbox 信息整合到树结构中，
实现从检索结果定位回原 PDF 的功能。
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field

from .base import BaseParser, SearchResult, LocationInfo, HeaderInfo

logger = logging.getLogger(__name__)


@dataclass
class ContentBlock:
    """内容块数据类"""
    type: str                    # text, image, header, aside_text
    text: Optional[str]          # 文本内容
    text_level: Optional[int]    # 标题层级
    bbox: List[float]            # [x1, y1, x2, y2] MinerU 坐标
    page_idx: int                # PDF 页码（从 0 开始）
    img_path: Optional[str] = None       # 图片路径
    image_caption: Optional[List[str]] = None  # 图片说明
    # 转换后的坐标
    pdf_bbox: Optional[List[float]] = field(default=None)  # PDF 坐标系的 bbox


class MinerUParser(BaseParser):
    """MinerU 解析结果处理器"""

    def __init__(self, content_list_path: str, md_path: Optional[str] = None, pdf_path: Optional[str] = None):
        """
        初始化 MinerU 解析器

        Args:
            content_list_path: MinerU 输出的 content_list.json 文件路径
            md_path: MinerU 输出的 .md 文件路径（可选，用于验证）
            pdf_path: 原始 PDF 文件路径（可选，用于坐标转换）
        """
        self.content_list_path = Path(content_list_path)
        self.md_path = Path(md_path) if md_path else None
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.content_blocks: List[ContentBlock] = []

        # 坐标转换参数
        self.pdf_width = 612  # 默认 PDF 宽度 (Letter)
        self.pdf_height = 792  # 默认 PDF 高度 (Letter)
        self.mineru_width = 1000  # MinerU 内部宽度
        self.mineru_height = 1000  # MinerU 内部高度

        # 如果提供了 PDF，获取实际尺寸
        if self.pdf_path and self.pdf_path.exists():
            self._init_pdf_dimensions()

        self._load_content_list()

        # 转换所有坐标
        if self.pdf_path:
            self._transform_all_coordinates()

    def _init_pdf_dimensions(self):
        """初始化 PDF 尺寸"""
        try:
            import fitz
            doc = fitz.open(str(self.pdf_path))
            if doc.page_count > 0:
                page = doc[0]
                self.pdf_width = page.rect.width
                self.pdf_height = page.rect.height
            doc.close()
        except Exception as e:
            logger.warning(f"Could not get PDF dimensions: {e}")

    def _load_content_list(self) -> None:
        """加载 content_list.json 文件"""
        with open(self.content_list_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        self.content_blocks = []

        # 检查是否是 v2 格式（列表的列表，每页一个子列表）
        if raw_data and isinstance(raw_data[0], list):
            # v2 格式：[[page0_items], [page1_items], ...]
            for page_idx, page_items in enumerate(raw_data):
                for item in page_items:
                    block = self._parse_v2_item(item, page_idx)
                    if block:
                        self.content_blocks.append(block)
        else:
            # v1 格式：直接的项目列表
            for item in raw_data:
                block = ContentBlock(
                    type=item.get('type', 'text'),
                    text=item.get('text'),
                    text_level=item.get('text_level'),
                    bbox=item.get('bbox', [0, 0, 0, 0]),
                    page_idx=item.get('page_idx', 0),
                    img_path=item.get('img_path'),
                    image_caption=item.get('image_caption')
                )
                self.content_blocks.append(block)

        logger.info(f"Loaded {len(self.content_blocks)} content blocks from {self.content_list_path}")

    def _parse_v2_item(self, item: Dict[str, Any], page_idx: int) -> Optional[ContentBlock]:
        """
        解析 v2 格式的项目

        v2 格式示例：
        {
            "type": "title",
            "content": {
                "title_content": [{"type": "text", "content": "Title"}],
                "level": 1
            },
            "bbox": [321, 64, 674, 97]
        }
        """
        item_type = item.get('type', 'text')
        bbox = item.get('bbox', [0, 0, 0, 0])
        content = item.get('content', {})

        text = None
        text_level = None
        img_path = None
        image_caption = None

        if item_type == 'title':
            # 标题
            title_content = content.get('title_content', [])
            text_parts = []
            for tc in title_content:
                if tc.get('type') == 'text':
                    text_parts.append(tc.get('content', ''))
            text = ''.join(text_parts)
            text_level = content.get('level', 1)

        elif item_type == 'paragraph':
            # 段落
            para_content = content.get('paragraph_content', [])
            text_parts = []
            for pc in para_content:
                pc_type = pc.get('type')
                if pc_type == 'text':
                    text_parts.append(pc.get('content', ''))
                elif pc_type == 'equation_inline':
                    text_parts.append(f"${pc.get('content', '')}$")
                # 可以添加更多类型的处理
            text = ''.join(text_parts)

        elif item_type == 'image':
            # 图片
            img_path = content.get('img_path')
            image_caption = content.get('image_caption', [])
            text = f"[Image: {img_path}]"

        return ContentBlock(
            type=item_type,
            text=text,
            text_level=text_level,
            bbox=bbox,
            page_idx=page_idx,
            img_path=img_path,
            image_caption=image_caption
        )

    def _transform_all_coordinates(self):
        """转换所有内容块的坐标到 PDF 坐标系"""
        for block in self.content_blocks:
            block.pdf_bbox = self._transform_bbox(block.bbox)

    def _transform_bbox(self, mineru_bbox: List[float]) -> List[float]:
        """
        将 MinerU bbox 转换为 PDF bbox

        Args:
            mineru_bbox: MinerU 坐标的 bbox [x1, y1, x2, y2]

        Returns:
            PDF 坐标的 bbox [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = mineru_bbox

        # 线性缩放到 PDF 尺寸
        pdf_x1 = (x1 / self.mineru_width) * self.pdf_width
        pdf_y1 = (y1 / self.mineru_height) * self.pdf_height
        pdf_x2 = (x2 / self.mineru_width) * self.pdf_width
        pdf_y2 = (y2 / self.mineru_height) * self.pdf_height

        return [pdf_x1, pdf_y1, pdf_x2, pdf_y2]

    def get_blocks_by_page(self, page_idx: int) -> List[ContentBlock]:
        """获取指定页的所有内容块"""
        return [b for b in self.content_blocks if b.page_idx == page_idx]

    def get_blocks_by_type(self, block_type: str) -> List[ContentBlock]:
        """获取指定类型的所有内容块"""
        return [b for b in self.content_blocks if b.type == block_type]

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
        for block in self.content_blocks:
            if block.text is None:
                continue
            
            match = False
            if fuzzy:
                match = query.lower() in block.text.lower()
            else:
                match = query in block.text
            
            if match:
                results.append(SearchResult(
                    page_idx=block.page_idx,
                    bbox=block.bbox,
                    text=block.text,
                    type=block.type,
                    context=block.text[:150] if block.text else "",
                    pdf_bbox=block.pdf_bbox
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
        # 首先查找标题
        for block in self.content_blocks:
            if block.text and title in block.text and block.text_level is not None:
                return LocationInfo(
                    page_idx=block.page_idx,
                    bbox=block.bbox,
                    type=block.type,
                    text=block.text,
                    page_size=[self.pdf_width, self.pdf_height]
                )
        
        # 如果没找到标题，尝试模糊匹配
        for block in self.content_blocks:
            if block.text and title.lower() in block.text.lower():
                return LocationInfo(
                    page_idx=block.page_idx,
                    bbox=block.bbox,
                    type=block.type,
                    text=block.text,
                    page_size=[self.pdf_width, self.pdf_height]
                )
        
        return None

    def get_headers(self) -> List[HeaderInfo]:
        """获取所有标题（实现 BaseParser 接口）"""
        headers = []
        for b in self.content_blocks:
            if b.text_level is not None:
                headers.append(HeaderInfo(
                    text=b.text or "",
                    level=b.text_level,
                    page_idx=b.page_idx,
                    bbox=b.bbox,
                    type=b.type
                ))
        return headers

    def get_headers_raw(self) -> List[ContentBlock]:
        """获取所有标题（返回原始 ContentBlock）"""
        return [b for b in self.content_blocks if b.text_level is not None]

    def get_total_pages(self) -> int:
        """获取总页数"""
        if not self.content_blocks:
            return 0
        return max(b.page_idx for b in self.content_blocks) + 1

    def find_text_location(self, search_text: str, fuzzy: bool = False) -> List[Dict[str, Any]]:
        """
        查找文本在 PDF 中的位置

        Args:
            search_text: 要查找的文本
            fuzzy: 是否模糊匹配

        Returns:
            匹配结果列表，每项包含 page_idx, bbox, pdf_bbox, text
        """
        results = []

        for block in self.content_blocks:
            if block.text is None:
                continue

            if fuzzy:
                if search_text.lower() in block.text.lower():
                    results.append({
                        'page_idx': block.page_idx,
                        'bbox': block.bbox,
                        'pdf_bbox': block.pdf_bbox,
                        'text': block.text,
                        'type': block.type
                    })
            else:
                if search_text in block.text:
                    results.append({
                        'page_idx': block.page_idx,
                        'bbox': block.bbox,
                        'pdf_bbox': block.pdf_bbox,
                        'text': block.text,
                        'type': block.type
                    })

        return results

    def get_node_location_info(self, node_title: str, node_text: str) -> Dict[str, Any]:
        """
        获取树节点在 PDF 中的位置信息

        Args:
            node_title: 节点标题
            node_text: 节点文本内容

        Returns:
            位置信息字典，包含 page_range, bboxes 等
        """
        # 查找标题位置
        title_matches = self.find_text_location(node_title, fuzzy=True)

        # 分析节点文本，找出涉及的页码
        # 通过匹配节点文本中的内容块来确定
        page_indices = set()
        bboxes = []

        # 简单方法：找到标题后的连续内容块
        if title_matches:
            # 使用第一个匹配的标题位置
            title_location = title_matches[0]
            start_page = title_location['page_idx']

            # 查找标题后的内容（同一页或后续页）
            found_title = False
            for block in self.content_blocks:
                if block.page_idx < start_page:
                    continue
                if block.page_idx == start_page and not found_title:
                    # 检查是否是标题
                    if block.text == node_title or (block.text and node_title in block.text):
                        found_title = True
                    continue

                if found_title:
                    # 遇到下一个同级或更高级标题时停止
                    if block.text_level is not None and block.text_level <= 2:
                        break
                    page_indices.add(block.page_idx)
                    if block.pdf_bbox:
                        bboxes.append({
                            'page_idx': block.page_idx,
                            'bbox': block.bbox,
                            'pdf_bbox': block.pdf_bbox,
                            'text': block.text[:100] if block.text else ''  # 前 100 字符
                        })

        return {
            'page_range': (
                min(page_indices) if page_indices else None,
                max(page_indices) if page_indices else None
            ),
            'total_pages': len(page_indices),
            'bboxes': bboxes,
            'title_location': title_matches[0] if title_matches else None
        }

    def export_location_map(self, tree_structure: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        为整个树结构导出位置映射

        Args:
            tree_structure: md2tree 生成的树结构

        Returns:
            节点 ID 到位置信息的映射
        """
        location_map = {}

        def traverse(nodes):
            for node in nodes:
                node_id = node.get('node_id')
                title = node.get('title', '')
                text = node.get('text', '')

                if node_id:
                    location_info = self.get_node_location_info(title, text)
                    location_map[node_id] = location_info

                if node.get('nodes'):
                    traverse(node['nodes'])

        traverse(tree_structure)
        return location_map


def add_location_info_to_tree(
    tree_structure: List[Dict[str, Any]],
    content_list_path: str,
    pdf_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    将 MinerU 的位置信息添加到树结构中

    Args:
        tree_structure: md2tree 生成的树结构
        content_list_path: MinerU content_list.json 路径
        pdf_path: 原始 PDF 文件路径（可选，用于坐标转换）

    Returns:
        增强后的树结构，每个节点包含 page_info
    """
    parser = MinerUParser(content_list_path, pdf_path=pdf_path)

    def add_location_to_node(node: Dict[str, Any]) -> Dict[str, Any]:
        """递归地为节点添加位置信息"""
        title = node.get('title', '')
        text = node.get('text', '')

        # 获取位置信息
        location_info = parser.get_node_location_info(title, text)

        # 添加到节点
        result = node.copy()
        result['page_info'] = {
            'page_range': location_info['page_range'],
            'total_pages': location_info['total_pages'],
            'title_location': location_info['title_location']
        }

        # 递归处理子节点
        if node.get('nodes'):
            result['nodes'] = [add_location_to_node(n) for n in node['nodes']]

        return result

    return [add_location_to_node(node) for node in tree_structure]


def create_pdf_link(
    pdf_path: str,
    page_idx: int,
    bbox: Optional[List[float]] = None
) -> str:
    """
    创建 PDF 链接，支持页面定位和区域高亮

    Args:
        pdf_path: PDF 文件路径
        page_idx: 页码（从 0 开始）
        bbox: 可选的边界框 [x1, y1, x2, y2]

    Returns:
        PDF 链接字符串
    """
    # PDF 页码从 1 开始显示
    display_page = page_idx + 1

    if bbox:
        # 带位置信息的链接
        x1, y1, x2, y2 = bbox
        return f"{pdf_path}#page={display_page}&bbox={x1},{y1},{x2},{y2}"
    else:
        # 仅页码的链接
        return f"{pdf_path}#page={display_page}"


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mineru_parser.py <content_list.json> [pdf_path]")
        sys.exit(1)

    content_list_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else None

    # 创建解析器
    parser = MinerUParser(content_list_path, pdf_path=pdf_path)

    # 打印统计信息
    print(f"\n=== MinerU Content Statistics ===")
    print(f"Total blocks: {len(parser.content_blocks)}")
    print(f"Total pages: {parser.get_total_pages()}")
    print(f"Headers: {len(parser.get_headers())}")
    print(f"Images: {len(parser.get_blocks_by_type('image'))}")

    if pdf_path:
        print(f"\n=== Coordinate Transform ===")
        print(f"PDF size: {parser.pdf_width} x {parser.pdf_height}")
        print(f"MinerU size: {parser.mineru_width} x {parser.mineru_height}")

    # 打印所有标题
    print(f"\n=== Headers ===")
    for header in parser.get_headers():
        indent = "  " * (header.text_level - 1) if header.text_level else ""
        print(f"{indent}[Page {header.page_idx + 1}] {header.text}")
        print(f"    MinerU bbox: {header.bbox}")
        if header.pdf_bbox:
            print(f"    PDF bbox: {[round(x, 2) for x in header.pdf_bbox]}")

    # 测试查找
    if len(sys.argv) > 3:
        search_text = sys.argv[3]
        print(f"\n=== Search for '{search_text}' ===")
        results = parser.find_text_location(search_text, fuzzy=True)
        for result in results:
            print(f"[Page {result['page_idx'] + 1}] {result['text'][:100]}")
            print(f"    MinerU bbox: {result['bbox']}")
            if result.get('pdf_bbox'):
                print(f"    PDF bbox: {[round(x, 2) for x in result['pdf_bbox']]}")
