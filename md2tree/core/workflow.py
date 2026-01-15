"""
PDF to Tree with Location Info Workflow

整合 MinerU 解析结果和 md2tree，生成带位置信息的树结构。
支持使用 middle.json 获取精确的 PDF 坐标。
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from .converter import md_to_tree, md_to_tree_async, print_toc
from ..llm.client import LLMConfig
from ..parsers.mineru import MinerUParser, add_location_info_to_tree, create_pdf_link
from ..parsers.middle_json import MiddleJSONParser, add_middlejson_location_to_tree
from ..pdf.viewer import PDFHighlighter, PDFLocationViewer, create_retrieval_result_html
from .tree import find_node_by_id, get_tree_stats

logger = logging.getLogger(__name__)


class PDFToTreeWorkflow:
    """PDF 到树的完整工作流"""

    def __init__(
        self,
        pdf_path: str,
        mineru_output_dir: str,
        md_path: Optional[str] = None,
        use_middle_json: bool = True
    ):
        """
        初始化工作流

        Args:
            pdf_path: 原始 PDF 文件路径
            mineru_output_dir: MinerU 输出目录（包含 content_list.json 和 middle.json）
            md_path: MinerU 输出的 .md 文件路径（如果不在默认位置）
            use_middle_json: 是否使用 middle.json 获取精确坐标（推荐）
        """
        self.pdf_path = Path(pdf_path)
        self.mineru_dir = Path(mineru_output_dir)
        self.use_middle_json = use_middle_json

        # 查找 content_list.json
        self.content_list_path = self._find_content_list()

        # 查找 middle.json（可选，用于精确坐标）
        self.middle_json_path = self._find_middle_json() if use_middle_json else None

        # 查找 .md 文件
        if md_path:
            self.md_path = Path(md_path)
        else:
            self.md_path = self._find_markdown()

        # 初始化 MinerU 解析器
        self.parser = MinerUParser(str(self.content_list_path))

        # 初始化 Middle JSON 解析器（如果可用）
        self.middle_parser = None
        if self.middle_json_path:
            try:
                self.middle_parser = MiddleJSONParser(str(self.middle_json_path))
                logger.info("Using middle.json for precise coordinates")
            except Exception as e:
                logger.warning(f"Could not load middle.json: {e}")
                self.middle_parser = None

        # 初始化 PDF 查看器
        self.pdf_viewer = PDFHighlighter(str(self.pdf_path))

    def _find_content_list(self) -> Path:
        """查找 content_list.json 文件"""
        # 尝试 v2 版本
        v2_path = self.mineru_dir / "vlm" / f"{self.pdf_path.stem}_content_list_v2.json"
        if v2_path.exists():
            return v2_path

        # 尝试 v1 版本
        v1_path = self.mineru_dir / "vlm" / f"{self.pdf_path.stem}_content_list.json"
        if v1_path.exists():
            return v1_path

        raise FileNotFoundError(f"content_list.json not found in {self.mineru_dir}")

    def _find_markdown(self) -> Path:
        """查找 .md 文件"""
        md_path = self.mineru_dir / "vlm" / f"{self.pdf_path.stem}.md"
        if md_path.exists():
            return md_path

        raise FileNotFoundError(f"Markdown file not found in {self.mineru_dir}")

    def _find_middle_json(self) -> Optional[Path]:
        """查找 middle.json 文件"""
        middle_path = self.mineru_dir / "vlm" / f"{self.pdf_path.stem}_middle.json"
        if middle_path.exists():
            return middle_path
        return None

    def close(self):
        """关闭资源"""
        self.pdf_viewer.close()

    def run_basic(
        self,
        output_path: Optional[str] = None,
        add_node_id: bool = True,
        keep_text: bool = True
    ) -> Dict[str, Any]:
        """
        运行基础工作流（无需 LLM）

        Args:
            output_path: 输出 JSON 路径
            add_node_id: 是否添加节点 ID
            keep_text: 是否保留文本内容

        Returns:
            树结构
        """
        logger.info("=== PDF to Tree Workflow ===")
        logger.info(f"PDF: {self.pdf_path}")
        logger.info(f"Markdown: {self.md_path}")
        logger.info(f"Content List: {self.content_list_path}")

        # 1. 转换 Markdown 为树
        logger.info("[1/3] Converting Markdown to tree...")
        tree_data = md_to_tree(
            str(self.md_path),
            add_node_id=add_node_id,
            keep_text=keep_text
        )

        # 2. 添加位置信息
        if self.middle_parser:
            logger.info("[2/3] Adding precise location info from middle.json...")
            tree_data['structure'] = add_middlejson_location_to_tree(
                tree_data['structure'],
                str(self.middle_json_path)
            )
            tree_data['location_source'] = 'middle.json'
        else:
            logger.info("[2/3] Adding location info from content_list.json...")
            tree_data['structure'] = add_location_info_to_tree(
                tree_data['structure'],
                str(self.content_list_path),
                pdf_path=str(self.pdf_path)
            )
            tree_data['location_source'] = 'content_list.json'

        # 3. 添加 PDF 路径
        tree_data['pdf_path'] = str(self.pdf_path)
        tree_data['pdf_name'] = self.pdf_path.name

        # 4. 添加统计信息
        logger.info("[3/3] Computing statistics...")
        stats = get_tree_stats(tree_data['structure'])
        tree_data['stats'] = stats

        # 5. 保存结果
        if output_path is None:
            output_path = f"./results/{self.pdf_path.stem}_with_locations.json"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tree_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Result saved to: {output_file}")
        logger.info(f"Statistics: total_nodes={stats['total_nodes']}, max_depth={stats['max_depth']}, leaf_nodes={stats['leaf_nodes']}")

        return tree_data

    async def run_advanced(
        self,
        output_path: Optional[str] = None,
        enable_thinning: bool = False,
        thinning_threshold: int = 5000,
        enable_summary: bool = False,
        summary_threshold: int = 200,
        enable_doc_description: bool = False,
        model: str = "glm-4.7"
    ) -> Dict[str, Any]:
        """
        运行高级工作流（带 LLM 功能）

        Args:
            output_path: 输出 JSON 路径
            enable_thinning: 是否应用树剪枝
            thinning_threshold: 剪枝阈值
            enable_summary: 是否生成摘要
            summary_threshold: 摘要阈值
            enable_doc_description: 是否生成文档描述
            model: LLM 模型名称

        Returns:
            树结构
        """
        logger.info("=== PDF to Tree Workflow (Advanced) ===")
        logger.info(f"PDF: {self.pdf_path}")
        logger.info(f"Markdown: {self.md_path}")
        logger.info(f"Model: {model}")

        config = LLMConfig(model=model)

        # 1. 转换 Markdown 为树（带 LLM 功能）
        logger.info("[1/3] Converting Markdown to tree with LLM...")
        tree_data = await md_to_tree_async(
            str(self.md_path),
            config=config,
            enable_thinning=enable_thinning,
            thinning_threshold=thinning_threshold,
            enable_summary=enable_summary,
            summary_token_threshold=summary_threshold,
            enable_doc_description=enable_doc_description
        )

        # 2. 添加位置信息
        if self.middle_parser:
            logger.info("[2/3] Adding precise location info from middle.json...")
            tree_data['structure'] = add_middlejson_location_to_tree(
                tree_data['structure'],
                str(self.middle_json_path)
            )
            tree_data['location_source'] = 'middle.json'
        else:
            logger.info("[2/3] Adding location info from content_list.json...")
            tree_data['structure'] = add_location_info_to_tree(
                tree_data['structure'],
                str(self.content_list_path),
                pdf_path=str(self.pdf_path)
            )
            tree_data['location_source'] = 'content_list.json'

        # 3. 添加 PDF 路径
        tree_data['pdf_path'] = str(self.pdf_path)
        tree_data['pdf_name'] = self.pdf_path.name

        # 4. 保存结果
        if output_path is None:
            suffix = "_advanced" if enable_thinning or enable_summary else ""
            output_path = f"./results/{self.pdf_path.stem}{suffix}_with_locations.json"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tree_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Result saved to: {output_file}")

        return tree_data

    def view_node(
        self,
        node_id: str,
        tree_data: Dict[str, Any],
        output_html: str,
        output_pdf: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查看节点在 PDF 中的位置

        Args:
            node_id: 节点 ID
            tree_data: 树结构数据
            output_html: 输出 HTML 路径
            output_pdf: 可选的输出高亮 PDF 路径

        Returns:
            节点信息
        """
        location_viewer = PDFLocationViewer(
            str(self.pdf_path),
            str(self.content_list_path)
        )

        result = location_viewer.view_node(
            node_id,
            tree_data['structure'],
            output_html,
            output_pdf
        )

        location_viewer.close()
        return result

    def search_and_locate_blocks(
        self,
        query: str,
        output_html: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        搜索文本并定位到具体的块（核心功能）

        这是用户的核心需求：从查询定位到页面中的具体块

        Args:
            query: 搜索查询
            output_html: 可选的输出 HTML 路径
            max_results: 最大结果数

        Returns:
            搜索结果，包含块的位置信息
        """
        if not self.middle_parser:
            logger.warning("middle.json not available, using content_list.json")
            # 降级到使用 content_list.json
            results = self.parser.find_text_location(query, fuzzy=True)
            return {
                'query': query,
                'source': 'content_list.json',
                'total_results': len(results),
                'results': results[:max_results]
            }

        # 使用 middle.json 进行精确的块级定位
        raw_results = self.middle_parser.search_and_locate(query)

        # 格式化结果
        formatted_results = []
        for i, result in enumerate(raw_results[:max_results]):
            formatted_results.append({
                'rank': i + 1,
                'page_idx': result['page_idx'],
                'page_num': result['page_idx'] + 1,  # 1-based for display
                'bbox': result['bbox'],
                'type': result['type'],
                'context': result['context'],
                'pdf_link': create_pdf_link(
                    str(self.pdf_path),
                    result['page_idx'],
                    result['bbox']
                ),
                'spans': result['full_info'].get('spans', [])[:5]  # 前5个spans
            })

        output = {
            'query': query,
            'source': 'middle.json',
            'total_results': len(raw_results),
            'returned_results': len(formatted_results),
            'results': formatted_results
        }

        # 生成 HTML 展示
        if output_html:
            self._create_search_results_html(output, output_html)

        return output

    def _create_search_results_html(
        self,
        search_output: Dict[str, Any],
        output_path: str
    ) -> None:
        """创建搜索结果的 HTML 展示"""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>Search Results</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        .result { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }",
            "        .rank { font-size: 24px; font-weight: bold; color: #007bff; }",
            "        .page-info { color: #666; margin: 5px 0; }",
            "        .context { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; }",
            "        .pdf-link { display: inline-block; margin: 5px 0; padding: 5px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; }",
            "        .pdf-link:hover { background: #0056b3; }",
            "        .bbox { font-family: monospace; font-size: 12px; color: #666; }",
            "        .type { display: inline-block; padding: 2px 8px; background: #e9ecef; border-radius: 3px; font-size: 12px; }",
            "    </style>",
            "</head>",
            "<body>",
            f"<h1>搜索结果: {search_output['query']}</h1>",
            f"<p>找到 {search_output['total_results']} 个结果，显示前 {search_output['returned_results']} 个</p>",
        ]

        for result in search_output['results']:
            html_parts.append(f"<div class='result'>")
            html_parts.append(f"    <span class='rank'>#{result['rank']}</span> ")
            html_parts.append(f"<span class='type'>{result['type']}</span>")
            html_parts.append(f"    <div class='page-info'>")
            html_parts.append(f"        第 {result['page_num']} 页 | ")
            html_parts.append(f"        bbox: <span class='bbox'>{result['bbox']}</span>")
            html_parts.append(f"    </div>")
            html_parts.append(f"    <div class='context'>{result['context']}</div>")
            html_parts.append(f"    <a href='{result['pdf_link']}' class='pdf-link' target='_blank'>在 PDF 中查看 →</a>")
            html_parts.append(f"</div>")

        html_parts.extend([
            "</body>",
            "</html>"
        ])

        html = "\n".join(html_parts)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Search results HTML saved to: {output_path}")

    def search_and_view(
        self,
        query: str,
        tree_data: Dict[str, Any],
        output_html: str
    ) -> List[Dict[str, Any]]:
        """
        搜索内容并查看位置

        Args:
            query: 搜索文本
            tree_data: 树结构数据
            output_html: 输出 HTML 路径

        Returns:
            匹配的节点列表
        """
        # 使用 MinerU 解析器搜索
        results = self.parser.find_text_location(query, fuzzy=True)

        # 创建 HTML 展示
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>Search Results</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        .result { margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; }",
            "        .page-link { color: #007bff; }",
            "    </style>",
            "</head>",
            "<body>",
            f"<h1>Search Results for '{query}'</h1>"
        ]

        for i, result in enumerate(results):
            page_idx = result['page_idx']
            bbox = result['bbox']
            text = result['text'][:200]

            html_parts.append(f"<div class='result'>")
            html_parts.append(f"    <strong>[Page {page_idx + 1}]</strong> ")
            html_parts.append(f"    <a href='{self.pdf_path}#page={page_idx + 1}' class='page-link' target='_blank'>View in PDF →</a>")
            html_parts.append(f"    <p>{text}...</p>")
            html_parts.append(f"    <small>bbox: {bbox}</small>")
            html_parts.append(f"</div>")

        html_parts.extend(["</body>", "</html>"])

        html = "\n".join(html_parts)

        with open(output_html, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Search results saved to: {output_html}")
        return results

    def create_retrieval_html(
        self,
        retrieval_results: List[Dict[str, Any]],
        tree_data: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        创建检索结果 HTML

        Args:
            retrieval_results: 检索结果列表
            tree_data: 树结构数据
            output_path: 输出 HTML 路径
        """
        create_retrieval_result_html(
            retrieval_results,
            tree_data['structure'],
            str(self.pdf_path),
            output_path
        )


def quick_process(
    pdf_path: str,
    mineru_output_dir: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    快速处理 PDF 到树的转换

    Args:
        pdf_path: PDF 文件路径
        mineru_output_dir: MinerU 输出目录
        output_path: 输出 JSON 路径

    Returns:
        树结构数据
    """
    workflow = PDFToTreeWorkflow(pdf_path, mineru_output_dir)
    try:
        result = workflow.run_basic(output_path=output_path)
        return result
    finally:
        workflow.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='PDF to Tree with Location Info')
    parser.add_argument('pdf_path', type=str, help='Path to PDF file')
    parser.add_argument('mineru_dir', type=str, help='MinerU output directory')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output JSON path')
    parser.add_argument('--advanced', action='store_true',
                        help='Use advanced workflow with LLM')
    parser.add_argument('--thinning', action='store_true',
                        help='Apply tree thinning')
    parser.add_argument('--summary', action='store_true',
                        help='Generate node summaries')
    parser.add_argument('--doc-description', action='store_true',
                        help='Generate document description')
    parser.add_argument('--model', type=str, default='glm-4.7',
                        help='LLM model name')

    args = parser.parse_args()

    workflow = PDFToTreeWorkflow(args.pdf_path, args.mineru_dir)

    try:
        if args.advanced:
            result = asyncio.run(workflow.run_advanced(
                output_path=args.output,
                enable_thinning=args.thinning,
                enable_summary=args.summary,
                enable_doc_description=args.doc_description,
                model=args.model
            ))
        else:
            result = workflow.run_basic(output_path=args.output)

        # 打印统计信息
        print("\n" + "=" * 60)
        print("TREE STRUCTURE")
        print("=" * 60)
        print_toc(result['structure'])

    finally:
        workflow.close()
