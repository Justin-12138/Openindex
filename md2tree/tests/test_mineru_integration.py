"""
测试 MinerU 集成功能

测试 mineru_parser, pdf_viewer 和 workflow 模块的所有功能

注意：这些测试需要实际的 PDF 和 MinerU 输出文件，如果没有这些文件，
测试将被跳过。要运行完整测试，请使用 `python -m md2tree.tests.test_mineru_integration`
"""

import json
import pytest
from pathlib import Path

from ..parsers.mineru import MinerUParser, ContentBlock, create_pdf_link
from ..pdf.viewer import PDFHighlighter, create_retrieval_result_html
from ..core.workflow import PDFToTreeWorkflow, quick_process
from ..core.converter import print_toc
from ..core.tree import find_node_by_id, get_tree_stats


class _TestResultHelper:
    """测试结果记录（使用下划线前缀以避免 pytest 识别为测试类）"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add(self, name: str, passed: bool, message: str = ""):
        self.tests.append({"name": name, "passed": passed, "message": message})
        if passed:
            self.passed += 1
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            print(f"  ✗ {name}: {message}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"测试结果: {self.passed}/{total} 通过")
        if self.failed > 0:
            print(f"失败: {self.failed}")
        print("=" * 60)


def test_mineru_parser():
    """测试 MinerU 解析器（需要实际文件，如果没有则跳过）"""
    # 检查测试文件是否存在
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")
    
    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")
    
    # 查找 content_list.json
    content_list_v1 = mineru_dir / "vlm" / f"{pdf_path.stem}_content_list.json"
    content_list_v2 = mineru_dir / "vlm" / f"{pdf_path.stem}_content_list_v2.json"
    
    if content_list_v2.exists():
        content_list_path = str(content_list_v2)
    elif content_list_v1.exists():
        content_list_path = str(content_list_v1)
    else:
        pytest.skip("找不到 content_list.json 文件")
    
    result = _TestResultHelper()
    print("\n[1] 测试 MinerU 解析器")

    try:
        parser = MinerUParser(content_list_path)
        result.add("初始化解析器", True)

        # 测试内容块数量
        block_count = len(parser.content_blocks)
        result.add(f"加载内容块 (数量: {block_count})", block_count > 0)

        # 测试获取页数
        total_pages = parser.get_total_pages()
        result.add(f"获取总页数 (页数: {total_pages})", total_pages == 7)

        # 测试获取标题
        headers = parser.get_headers()
        result.add(f"获取标题 (数量: {len(headers)})", len(headers) == 12)

        # 测试按类型获取内容块
        images = parser.get_blocks_by_type('image')
        result.add(f"获取图片 (数量: {len(images)})", len(images) == 8)

        # 测试按页获取内容块
        page_0_blocks = parser.get_blocks_by_page(0)
        result.add(f"按页获取内容块 (第1页: {len(page_0_blocks)}个)", len(page_0_blocks) > 0)

        # 测试文本查找
        results = parser.find_text_location("memory wall", fuzzy=True)
        result.add(f"模糊查找 'memory wall' (结果: {len(results)}个)", len(results) >= 3)

        # 测试获取节点位置信息
        location_info = parser.get_node_location_info("I. INTRODUCTION", "")
        result.add(
            "获取节点位置信息",
            location_info['title_location'] is not None,
            f"page_range: {location_info['page_range']}"
        )

    except Exception as e:
        result.add("MinerU 解析器测试", False, str(e))


def test_pdf_highlighter():
    """测试 PDF 高亮工具（需要实际文件，如果没有则跳过）"""
    # 检查测试文件是否存在
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")
    
    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")
    
    # 查找 content_list.json
    content_list_v1 = mineru_dir / "vlm" / f"{pdf_path.stem}_content_list.json"
    content_list_v2 = mineru_dir / "vlm" / f"{pdf_path.stem}_content_list_v2.json"
    
    if content_list_v2.exists():
        content_list_path = str(content_list_v2)
    elif content_list_v1.exists():
        content_list_path = str(content_list_v1)
    else:
        pytest.skip("找不到 content_list.json 文件")
    
    result = _TestResultHelper()
    pdf_path_str = str(pdf_path)
    print("\n[2] 测试 PDF 高亮工具")

    try:
        highlighter = PDFHighlighter(pdf_path_str)
        result.add("初始化 PDF 高亮器", True)

        # 测试页数
        page_count = highlighter.doc.page_count
        result.add(f"PDF 页数 (页数: {page_count})", page_count == 7)

        # 测试创建 HTML 预览
        output_html = "/tmp/test_page_preview.html"
        highlighter.create_page_html(0, [], output_html)
        result.add(f"创建 HTML 预览", Path(output_html).exists())

        # 测试提取带 bbox 的文本
        text_with_bbox = highlighter.extract_text_with_bbox(0)
        result.add(f"提取带 bbox 文本 (块数: {len(text_with_bbox)})", len(text_with_bbox) > 0)

        highlighter.close()

    except Exception as e:
        result.add("PDF 高亮工具测试", False, str(e))


def test_workflow():
    """测试完整工作流（需要实际文件，如果没有则跳过）"""
    # 检查测试文件是否存在
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")
    
    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")
    
    result = _TestResultHelper()
    pdf_path_str = str(pdf_path)
    mineru_dir_str = str(mineru_dir)
    print("\n[3] 测试完整工作流")

    try:
        workflow = PDFToTreeWorkflow(pdf_path_str, mineru_dir_str)
        result.add("初始化工作流", True)

        # 测试基础转换
        output_json = "/tmp/test_workflow_output.json"
        tree_data = workflow.run_basic(output_path=output_json)

        result.add("基础转换", Path(output_json).exists())

        # 检查树结构
        structure = tree_data.get('structure', [])
        result.add(f"树结构生成 (节点数: {len(structure)})", len(structure) == 12)

        # 检查位置信息
        has_page_info = all('page_info' in node for node in structure)
        result.add("位置信息添加", has_page_info)

        # 检查统计信息
        stats = tree_data.get('stats', {})
        has_stats = 'total_nodes' in stats
        result.add(f"统计信息 (总节点: {stats.get('total_nodes', 0)})", has_stats)

        # 测试查看节点
        node_id = structure[0].get('node_id')
        if node_id:
            output_html = "/tmp/test_node_view.html"
            workflow.view_node(node_id, tree_data, output_html)
            result.add(f"查看节点 (node_id: {node_id})", Path(output_html).exists())

        # 测试搜索功能
        output_search_html = "/tmp/test_search_results.html"
        workflow.search_and_view("memory wall", tree_data, output_search_html)
        result.add("搜索功能", Path(output_search_html).exists())

        workflow.close()

    except Exception as e:
        result.add("工作流测试", False, str(e))


def test_quick_process():
    """测试快速处理函数（需要实际文件，如果没有则跳过）"""
    # 检查测试文件是否存在
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")
    
    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")
    
    result = _TestResultHelper()
    pdf_path_str = str(pdf_path)
    mineru_dir_str = str(mineru_dir)
    print("\n[4] 测试快速处理")

    try:
        output_json = "/tmp/test_quick_process.json"
        tree_data = quick_process(pdf_path_str, mineru_dir_str, output_json)

        result.add("快速处理", Path(output_json).exists())

        # 验证数据结构
        required_fields = ['doc_name', 'structure', 'pdf_path', 'stats']
        has_all_fields = all(field in tree_data for field in required_fields)
        result.add("数据结构完整性", has_all_fields)

    except Exception as e:
        result.add("快速处理测试", False, str(e))


def test_pdf_link_generation():
    """测试 PDF 链接生成"""
    result = _TestResultHelper()
    print("\n[5] 测试 PDF 链接生成")

    try:
        # 测试基础链接
        link1 = create_pdf_link("test.pdf", 0)
        expected1 = "test.pdf#page=1"
        result.add(f"基础链接生成", link1 == expected1, f"期望: {expected1}, 实际: {link1}")

        # 测试带 bbox 链接
        link2 = create_pdf_link("test.pdf", 0, [100, 200, 300, 400])
        expected2 = "test.pdf#page=1&bbox=100,200,300,400"
        result.add(f"带 bbox 链接", link2 == expected2, f"期望: {expected2}, 实际: {link2}")

    except Exception as e:
        result.add("PDF 链接生成测试", False, str(e))


def test_retrieval_html():
    """测试检索结果 HTML 生成（需要实际文件，如果没有则跳过）"""
    # 检查测试文件是否存在
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")
    
    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")
    
    # 查找 content_list.json
    content_list_v1 = mineru_dir / "vlm" / f"{pdf_path.stem}_content_list.json"
    content_list_v2 = mineru_dir / "vlm" / f"{pdf_path.stem}_content_list_v2.json"
    
    if content_list_v2.exists():
        content_list_path = str(content_list_v2)
    elif content_list_v1.exists():
        content_list_path = str(content_list_v1)
    else:
        pytest.skip("找不到 content_list.json 文件")
    
    result = _TestResultHelper()
    pdf_path_str = str(pdf_path)
    print("\n[6] 测试检索结果 HTML")

    try:
        # 创建测试树结构
        test_tree = [
            {
                "title": "Test Node 1",
                "node_id": "0001",
                "page_info": {
                    "title_location": {"page_idx": 0},
                    "page_range": (0, 1)
                },
                "summary": "This is a test summary for node 1"
            },
            {
                "title": "Test Node 2",
                "node_id": "0002",
                "page_info": {
                    "title_location": {"page_idx": 2},
                    "page_range": (2, 2)
                },
                "summary": "This is a test summary for node 2"
            }
        ]

        # 模拟检索结果
        retrieval_results = [
            {"node_id": "0001", "score": 0.95},
            {"node_id": "0002", "score": 0.87}
        ]

        output_html = "/tmp/test_retrieval_results.html"
        create_retrieval_result_html(
            retrieval_results,
            test_tree,
            pdf_path_str,
            output_html
        )

        result.add("检索结果 HTML", Path(output_html).exists())

    except Exception as e:
        result.add("检索结果 HTML 测试", False, str(e))


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("MinerU 集成功能测试")
    print("=" * 60)

    result = _TestResultHelper()

    # 测试路径
    pdf_path = "data/pdfs/2403.14123v1_origin.pdf"
    mineru_dir = "data/pdfs/res/2403.14123v1_origin"

    # 检查文件是否存在
    if not Path(pdf_path).exists():
        print(f"错误: PDF 文件不存在: {pdf_path}")
        return

    content_list_v1 = Path(mineru_dir) / "vlm" / f"{Path(pdf_path).stem}_content_list.json"
    content_list_v2 = Path(mineru_dir) / "vlm" / f"{Path(pdf_path).stem}_content_list_v2.json"

    if content_list_v2.exists():
        content_list_path = str(content_list_v2)
    elif content_list_v1.exists():
        content_list_path = str(content_list_v1)
    else:
        print(f"错误: 找不到 content_list.json")
        return

    print(f"PDF: {pdf_path}")
    print(f"Content List: {content_list_path}")

    # 运行测试
    test_mineru_parser(content_list_path, result)
    test_pdf_highlighter(pdf_path, content_list_path, result)
    test_workflow(pdf_path, mineru_dir, result)
    test_quick_process(pdf_path, mineru_dir, result)
    test_pdf_link_generation(result)
    test_retrieval_html(pdf_path, content_list_path, result)

    # 打印测试摘要
    result.summary()

    # 打印生成的文件
    print("\n生成的测试文件:")
    test_files = [
        "/tmp/test_page_preview.html",
        "/tmp/test_workflow_output.json",
        "/tmp/test_node_view.html",
        "/tmp/test_search_results.html",
        "/tmp/test_quick_process.json",
        "/tmp/test_retrieval_results.html"
    ]
    for f in test_files:
        exists = "✓" if Path(f).exists() else "✗"
        print(f"  {exists} {f}")

    # 打印树结构示例
    print("\n" + "=" * 60)
    print("树结构示例")
    print("=" * 60)

    try:
        with open("/tmp/test_workflow_output.json", 'r', encoding='utf-8') as f:
            tree_data = json.load(f)

        print(f"\n文档: {tree_data.get('doc_name')}")
        print(f"PDF: {tree_data.get('pdf_name')}")

        print("\n目录:")
        print_toc(tree_data['structure'])

        print("\n第一个节点的 page_info:")
        if tree_data['structure']:
            first_node = tree_data['structure'][0]
            page_info = first_node.get('page_info', {})
            print(f"  标题: {first_node.get('title')}")
            print(f"  页码范围: {page_info.get('page_range')}")
            print(f"  总页数: {page_info.get('total_pages')}")
            title_loc = page_info.get('title_location', {})
            print(f"  标题位置: page={title_loc.get('page_idx') + 1}, bbox={title_loc.get('bbox')}")

    except Exception as e:
        print(f"无法读取输出文件: {e}")

    print("\n" + "=" * 60)
    print("提示: 在浏览器中打开 HTML 文件查看可视化结果")
    print("  - /tmp/test_page_preview.html - PDF 页面预览")
    print("  - /tmp/test_node_view.html - 节点位置视图")
    print("  - /tmp/test_search_results.html - 搜索结果")
    print("  - /tmp/test_retrieval_results.html - 检索结果展示")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
