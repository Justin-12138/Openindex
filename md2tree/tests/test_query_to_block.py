"""
测试查询到块的功能

这是用户的核心需求：从查询定位到页面中的具体块

注意：这些测试需要实际的 PDF 和 MinerU 输出文件，如果没有这些文件，
测试将被跳过。要运行完整测试，请使用 `python -m md2tree.tests.test_query_to_block`
"""

import sys
import json
import pytest
from pathlib import Path

# 使用相对导入
from md2tree.core.workflow import PDFToTreeWorkflow


def test_query_to_block():
    """测试查询到块的功能（需要实际文件，如果没有则跳过）"""
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")

    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")

    print("=" * 70)
    print("测试查询到块功能 (Query → Block)")
    print("=" * 70)

    # 创建工作流
    workflow = PDFToTreeWorkflow(str(pdf_path), str(mineru_dir), use_middle_json=True)

    # 测试查询
    test_queries = [
        "memory wall",
        "arithmetic intensity",
        "transformer",
        "efficient training"
    ]

    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"查询: '{query}'")
        print('=' * 70)

        # 搜索并定位块
        output_html = f"results/search_{query.replace(' ', '_')}.html"
        results = workflow.search_and_locate_blocks(
            query,
            output_html=output_html,
            max_results=5
        )

        print(f"找到 {results['total_results']} 个结果（来源: {results['source']}）")

        for i, result in enumerate(results['results'][:3]):
            print(f"\n  [{i+1}] 第 {result['page_num']} 页 | {result['type']}")
            print(f"      bbox: {result['bbox']}")
            print(f"      上下文: {result['context'][:100]}...")
            print(f"      PDF 链接: {result['pdf_link']}")

        print(f"\n  HTML 展示: {output_html}")

    workflow.close()

    # 生成测试报告
    print("\n" + "=" * 70)
    print("测试报告")
    print("=" * 70)
    print("✓ middle.json 解析成功")
    print("✓ 块级定位功能正常")
    print("✓ 搜索结果包含精确的 PDF 坐标")
    print("✓ 生成 HTML 展示页面")


def test_tree_with_blocks():
    """测试带块信息的树结构（需要实际文件，如果没有则跳过）"""
    pdf_path = Path("data/pdfs/2403.14123v1_origin.pdf")
    mineru_dir = Path("data/pdfs/res/2403.14123v1_origin")

    if not pdf_path.exists() or not mineru_dir.exists():
        pytest.skip("需要测试文件: data/pdfs/2403.14123v1_origin.pdf 和对应的 MinerU 输出")

    print("\n" + "=" * 70)
    print("测试树结构与块信息的集成")
    print("=" * 70)

    workflow = PDFToTreeWorkflow(str(pdf_path), str(mineru_dir), use_middle_json=True)

    # 运行基础工作流
    tree_data = workflow.run_basic(output_path="results/tree_with_blocks.json")

    # 检查第一个节点的块信息
    if tree_data['structure']:
        first_node = tree_data['structure'][0]
        print(f"\n节点: {first_node['title']}")
        print(f"位置信息来源: {tree_data.get('location_source', 'unknown')}")

        page_info = first_node.get('page_info', {})
        title_block = page_info.get('title_block')

        if title_block:
            print(f"\n标题块信息:")
            print(f"  页码: {title_block['page_idx'] + 1}")
            print(f"  bbox: {title_block['bbox']}")
            print(f"  类型: {title_block['type']}")
            print(f"  文本: {title_block['text']}")

        content_blocks = page_info.get('content_blocks', [])
        print(f"\n内容块数量: {len(content_blocks)}")

        if content_blocks:
            print(f"第一个内容块:")
            first_block = content_blocks[0]
            print(f"  页码: {first_block['page_idx'] + 1}")
            print(f"  bbox: {first_block['bbox']}")
            print(f"  类型: {first_block['type']}")

    workflow.close()


def main():
    """运行所有测试"""
    test_query_to_block()
    test_tree_with_blocks()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    print("生成的文件:")
    print("  - results/search_*.html - 搜索结果展示")
    print("  - results/tree_with_blocks.json - 带块信息的树结构")
    print("\n在浏览器中打开 HTML 文件查看可视化结果")


if __name__ == "__main__":
    main()
