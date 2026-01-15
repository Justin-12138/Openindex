"""
PDF Viewer and Highlighter

提供在 PDF 中定位和高亮内容的功能，支持生成带高亮的 PDF 和 HTML 预览。
"""

import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class PDFHighlighter:
    """PDF 高亮定位工具"""

    def __init__(self, pdf_path: str):
        """
        初始化 PDF 高亮器

        Args:
            pdf_path: PDF 文件路径
        """
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(pdf_path)

        # 获取 PDF 页面尺寸（用于归一化坐标）
        if self.doc.page_count > 0:
            first_page = self.doc[0]
            self.page_width = first_page.rect.width
            self.page_height = first_page.rect.height
        else:
            self.page_width = 0
            self.page_height = 0

    def close(self):
        """关闭 PDF 文档"""
        self.doc.close()

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时关闭资源"""
        self.close()
        return False

    def highlight_bbox(
        self,
        page_idx: int,
        bbox: List[float],
        color: Tuple[float, float, float] = (1, 1, 0),
        opacity: float = 0.3
    ) -> fitz.Page:
        """
        在指定页面的 bbox 区域添加高亮

        Args:
            page_idx: 页码（从 0 开始）
            bbox: 边界框 [x1, y1, x2, y2]
            color: RGB 颜色 (0-1)
            opacity: 不透明度 (0-1)

        Returns:
            修改后的页面对象
        """
        if page_idx >= len(self.doc):
            raise ValueError(f"Page {page_idx} out of range (total: {len(self.doc)})")

        page = self.doc[page_idx]
        rect = fitz.Rect(bbox)

        # 添加高亮注释
        highlight = page.add_highlight_annot(rect)
        highlight.set_colors(stroke=color)
        highlight.set_opacity(opacity)
        highlight.update()

        return page

    def highlight_node(
        self,
        page_idx: int,
        bboxes: List[Dict[str, Any]],
        output_path: str,
        color: Tuple[float, float, float] = (1, 1, 0)
    ) -> None:
        """
        高亮多个 bbox 区域并保存 PDF

        Args:
            page_idx: 页码
            bboxes: bbox 列表，每项包含 bbox 和可选的 text
            output_path: 输出 PDF 路径
            color: 高亮颜色
        """
        # 复制文档以避免修改原文件
        output_doc = fitz.open()

        # 复制所有页面
        for page in self.doc:
            output_doc.new_page(width=page.rect.width, height=page.rect.height)
            output_page = output_doc[-1]
            output_page.show_pdf_page(output_page.rect, self.doc, page.number)

        # 高亮指定页面
        if page_idx < len(output_doc):
            output_page = output_doc[page_idx]
            for item in bboxes:
                bbox = item.get('bbox', [0, 0, 0, 0])
                rect = fitz.Rect(bbox)

                # 添加高亮
                highlight = output_page.add_highlight_annot(rect)
                highlight.set_colors(stroke=color)
                highlight.set_opacity(0.3)
                highlight.update()

        output_doc.save(output_path)
        output_doc.close()

    def create_page_html(
        self,
        page_idx: int,
        highlights: Optional[List[Dict[str, Any]]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        创建带高亮的 HTML 页面预览

        Args:
            page_idx: 页码
            highlights: 高亮区域列表，每项包含 bbox 和可选的 text
            output_path: 可选的输出 HTML 文件路径

        Returns:
            HTML 字符串
        """
        if page_idx >= len(self.doc):
            raise ValueError(f"Page {page_idx} out of range")

        page = self.doc[page_idx]

        # 渲染页面为图片
        mat = fitz.Matrix(2, 2)  # 2x 缩放以提高质量
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        # 转换为 base64
        import base64
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        # 构建 HTML
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <style>",
            "        body { margin: 0; padding: 20px; background: #f0f0f0; }",
            "        .container { position: relative; display: inline-block; }",
            "        .pdf-page { max-width: 100%; height: auto; }",
            "        .highlight {",
            "            position: absolute;",
            "            border: 3px solid yellow;",
            "            background: rgba(255, 255, 0, 0.3);",
            "            pointer-events: none;",
            "        }",
            "        .highlight-label {",
            "            position: absolute;",
            "            background: yellow;",
            "            padding: 2px 5px;",
            "            font-size: 12px;",
            "            font-weight: bold;",
            "            z-index: 10;",
            "        }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>Page {page_idx + 1}</h1>",
            "    <div class='container'>"
        ]

        # 添加图片
        page_width = pix.width
        page_height = pix.height
        html_parts.append(f"        <img class='pdf-page' src='data:image/png;base64,{img_base64}' width='{page_width}' height='{page_height}'>")

        # 添加高亮
        if highlights:
            for i, highlight in enumerate(highlights):
                bbox = highlight.get('bbox', [0, 0, 0, 0])
                x1, y1, x2, y2 = bbox

                # 转换为百分比位置（考虑 2x 缩放）
                left = (x1 / page.rect.width) * 100
                top = (y1 / page.rect.height) * 100
                width = ((x2 - x1) / page.rect.width) * 100
                height = ((y2 - y1) / page.rect.height) * 100

                html_parts.append(f"        <div class='highlight' style='left: {left}%; top: {top}%; width: {width}%; height: {height}%;'></div>")

                # 添加标签
                text = highlight.get('text', '')
                if text:
                    html_parts.append(f"        <div class='highlight-label' style='left: {left}%; top: {top}%;'>{i + 1}</div>")

        html_parts.extend([
            "    </div>",
            "    <div style='margin-top: 20px;'>"
        ])

        # 添加高亮说明
        if highlights:
            html_parts.append("        <h2>Highlighted Sections</h2>")
            for i, highlight in enumerate(highlights):
                text = highlight.get('text', '')
                page_idx_h = highlight.get('page_idx', page_idx)
                html_parts.append(f"        <p><strong>{i + 1}.</strong> [Page {page_idx_h + 1}] {text[:200]}...</p>")

        html_parts.extend([
            "    </div>",
            "</body>",
            "</html>"
        ])

        html = "\n".join(html_parts)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"HTML preview saved to: {output_path}")

        return html

    def extract_text_with_bbox(self, page_idx: int) -> List[Dict[str, Any]]:
        """
        提取页面的文本和 bbox 信息

        Args:
            page_idx: 页码

        Returns:
            文本块列表，每项包含 text, bbox
        """
        if page_idx >= len(self.doc):
            raise ValueError(f"Page {page_idx} out of range")

        page = self.doc[page_idx]
        blocks = page.get_text("dict")["blocks"]

        results = []
        for block in blocks:
            if "lines" in block:  # 文本块
                for line in block["lines"]:
                    for span in line["spans"]:
                        results.append({
                            "text": span["text"],
                            "bbox": list(span["bbox"]),
                            "font": span["font"],
                            "size": span["size"]
                        })

        return results


class PDFLocationViewer:
    """PDF 定位查看器 - 整合 MinerU 结果和 PDF"""

    def __init__(self, pdf_path: str, content_list_path: str):
        """
        初始化定位查看器

        Args:
            pdf_path: 原始 PDF 文件路径
            content_list_path: MinerU content_list.json 路径
        """
        from ..parsers.mineru import MinerUParser

        self.pdf_path = Path(pdf_path)
        self.highlighter = PDFHighlighter(pdf_path)
        self.parser = MinerUParser(content_list_path)

    def close(self):
        """关闭资源"""
        self.highlighter.close()

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时关闭资源"""
        self.close()
        return False

    def view_node(
        self,
        node_id: str,
        tree_structure: List[Dict[str, Any]],
        output_html: str,
        output_pdf: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查看树节点在 PDF 中的位置

        Args:
            node_id: 节点 ID
            tree_structure: 树结构
            output_html: 输出 HTML 预览路径
            output_pdf: 可选的输出高亮 PDF 路径

        Returns:
            节点信息和位置
        """
        from ..core.tree import find_node_by_id

        # 查找节点
        node = find_node_by_id(tree_structure, node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        title = node.get('title', '')
        page_info = node.get('page_info', {})

        # 收集所有 bbox
        highlights = []
        page_range = page_info.get('page_range', (None, None))
        title_location = page_info.get('title_location')

        if title_location:
            highlights.append({
                'page_idx': title_location['page_idx'],
                'bbox': title_location['bbox'],
                'text': f"Title: {title}"
            })

        # 查找节点内容的位置
        if page_range[0] is not None:
            for page_idx in range(page_range[0], page_range[1] + 1):
                blocks = self.parser.get_blocks_by_page(page_idx)
                for block in blocks:
                    if block.type == 'text' and block.text and block.text in node.get('text', ''):
                        highlights.append({
                            'page_idx': block.page_idx,
                            'bbox': block.bbox,
                            'text': block.text[:100]
                        })

        # 创建 HTML 预览
        if highlights:
            main_page = highlights[0]['page_idx']
            self.highlighter.create_page_html(
                main_page,
                highlights,
                output_html
            )

        # 创建高亮 PDF
        if output_pdf and highlights:
            # 按页分组高亮
            highlights_by_page = {}
            for h in highlights:
                page_idx = h['page_idx']
                if page_idx not in highlights_by_page:
                    highlights_by_page[page_idx] = []
                highlights_by_page[page_idx].append(h)

            # 高亮第一页
            first_page = list(highlights_by_page.keys())[0]
            self.highlighter.highlight_node(
                first_page,
                highlights_by_page[first_page],
                output_pdf
            )

        return {
            'node': node,
            'highlights': highlights,
            'page_range': page_range
        }


def create_retrieval_result_html(
    retrieval_results: List[Dict[str, Any]],
    tree_structure: List[Dict[str, Any]],
    pdf_path: str,
    output_path: str
) -> None:
    """
    创建检索结果的 HTML 展示页面

    Args:
        retrieval_results: 检索结果列表
        tree_structure: 树结构
        pdf_path: PDF 文件路径
        output_path: 输出 HTML 路径
    """
    from ..core.tree import find_node_by_id

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <meta charset='UTF-8'>",
        "    <title>Retrieval Results</title>",
        "    <style>",
        "        body { font-family: Arial, sans-serif; margin: 20px; }",
        "        .result { margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }",
        "        .node-title { font-size: 18px; font-weight: bold; color: #333; }",
        "        .node-summary { margin-top: 10px; color: #555; }",
        "        .page-info { margin-top: 10px; font-size: 14px; color: #007bff; }",
        "        .pdf-link { display: inline-block; margin-top: 10px; padding: 5px 10px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; }",
        "        .pdf-link:hover { background: #0056b3; }",
        "    </style>",
        "</head>",
        "<body>",
        f"    <h1>Retrieval Results for {Path(pdf_path).stem}</h1>"
    ]

    for i, result in enumerate(retrieval_results):
        node_id = result.get('node_id')
        node = find_node_by_id(tree_structure, node_id)

        if not node:
            continue

        html_parts.append(f"    <div class='result'>")
        html_parts.append(f"        <div class='node-title'>{i + 1}. {node.get('title', 'Unknown')}</div>")

        if node.get('summary'):
            html_parts.append(f"        <div class='node-summary'>{node.get('summary')}</div>")
        elif node.get('prefix_summary'):
            html_parts.append(f"        <div class='node-summary'>{node.get('prefix_summary')}</div>")

        # 页面信息
        page_info = node.get('page_info', {})
        page_range = page_info.get('page_range', (None, None))
        title_location = page_info.get('title_location')

        if page_range[0] is not None:
            start_page = page_range[0] + 1  # 转换为 1-based
            end_page = page_range[1] + 1
            html_parts.append(f"        <div class='page-info'>📍 Pages {start_page}-{end_page}</div>")

        # PDF 链接
        if title_location:
            page_num = title_location['page_idx'] + 1
            html_parts.append(f"        <a href='{pdf_path}#page={page_num}' class='pdf-link' target='_blank'>View in PDF →</a>")

        html_parts.append("    </div>")

    html_parts.extend([
        "</body>",
        "</html>"
    ])

    html = "\n".join(html_parts)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"Retrieval results HTML saved to: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python pdf_viewer.py <pdf_path> <content_list.json> [page_idx]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    content_list_path = sys.argv[2]

    viewer = PDFHighlighter(pdf_path)

    if len(sys.argv) > 3:
        page_idx = int(sys.argv[3])
        output_html = f"/tmp/page_{page_idx + 1}.html"
        viewer.create_page_html(page_idx, [], output_html)
        print(f"Created HTML preview: {output_html}")
    else:
        print(f"PDF has {viewer.doc.page_count} pages")

    viewer.close()
