"""
MinerU 集成演示

展示如何使用 MinerU 解析和 PDF 定位功能
"""

from pathlib import Path

from ..parsers.mineru import MinerUParser, create_pdf_link
from ..pdf.viewer import PDFHighlighter
from ..core.workflow import PDFToTreeWorkflow
from ..core.converter import print_toc


def demo_basic_workflow():
    """演示基础工作流"""
    print("=" * 70)
    print("演示 1: 基础工作流 - PDF 到带位置信息的树")
    print("=" * 70)

    pdf_path = "data/pdfs/2403.14123v1_origin.pdf"
    mineru_dir = "data/pdfs/res/2403.14123v1_origin"

    workflow = PDFToTreeWorkflow(pdf_path, mineru_dir)

    # 运行基础转换
    output_path = "results/demo_output.json"
    tree_data = workflow.run_basic(output_path=output_path)

    # 打印结果
    print("\n📊 转换结果:")
    print(f"  文档名称: {tree_data['doc_name']}")
    print(f"  PDF 路径: {tree_data['pdf_path']}")
    print(f"  总节点数: {tree_data['stats']['total_nodes']}")
    print(f"  最大深度: {tree_data['stats']['max_depth']}")

    workflow.close()
    print(f"\n✓ 结果已保存到: {output_path}")
    return tree_data


def demo_parser():
    """演示 MinerU 解析器"""
    print("\n" + "=" * 70)
    print("演示 2: MinerU 解析器 - 查找文本位置")
    print("=" * 70)

    content_list_path = "data/pdfs/res/2403.14123v1_origin/vlm/2403.14123v1_origin_content_list_v2.json"

    parser = MinerUParser(content_list_path)

    # 查找文本
    search_term = "memory wall"
    results = parser.find_text_location(search_term, fuzzy=True)

    print(f"\n🔍 搜索 '{search_term}' 找到 {len(results)} 个结果:")
    for i, result in enumerate(results[:5]):  # 只显示前 5 个
        page_num = result['page_idx'] + 1
        bbox = result['bbox']
        text = result['text'][:60] + "..." if len(result['text']) > 60 else result['text']
        print(f"  [{i+1}] 第 {page_num} 页 | bbox: {bbox}")
        print(f"      {text}")

    # 生成 PDF 链接
    if results:
        first_result = results[0]
        link = create_pdf_link(
            "paper.pdf",
            first_result['page_idx'],
            first_result['bbox']
        )
        print(f"\n📎 PDF 链接示例: {link}")


def demo_pdf_viewer():
    """演示 PDF 查看器"""
    print("\n" + "=" * 70)
    print("演示 3: PDF 查看器 - 创建页面预览")
    print("=" * 70)

    pdf_path = "data/pdfs/2403.14123v1_origin.pdf"

    viewer = PDFHighlighter(pdf_path)

    # 创建第一页的 HTML 预览
    output_html = "results/demo_page_preview.html"
    viewer.create_page_html(0, [], output_html)

    print(f"\n🖼️  创建了第 1 页的 HTML 预览")
    print(f"   保存位置: {output_html}")
    print(f"   在浏览器中打开查看")

    # 提取文本和位置信息
    text_with_bbox = viewer.extract_text_with_bbox(0)
    print(f"\n📝 第 1 页包含 {len(text_with_bbox)} 个文本块")

    viewer.close()


def demo_node_location(tree_data):
    """演示节点定位"""
    print("\n" + "=" * 70)
    print("演示 4: 节点定位 - 查找节点在 PDF 中的位置")
    print("=" * 70)

    pdf_path = "data/pdfs/2403.14123v1_origin.pdf"
    mineru_dir = "data/pdfs/res/2403.14123v1_origin"

    workflow = PDFToTreeWorkflow(pdf_path, mineru_dir)

    # 获取第一个节点
    first_node = tree_data['structure'][0]
    node_id = first_node['node_id']

    print(f"\n📍 节点: {first_node['title']}")
    print(f"   ID: {node_id}")

    page_info = first_node.get('page_info', {})
    page_range = page_info.get('page_range')
    title_loc = page_info.get('title_location')

    if page_range and page_range[0] is not None:
        start_page = page_range[0] + 1
        end_page = page_range[1] + 1
        print(f"   页码范围: {start_page} - {end_page}")

    if title_loc:
        page_num = title_loc['page_idx'] + 1
        bbox = title_loc['bbox']
        print(f"   标题位置: 第 {page_num} 页")
        print(f"   bbox: {bbox}")

        # 生成节点视图
        output_html = "results/demo_node_view.html"
        output_pdf = "results/demo_node_highlighted.pdf"
        workflow.view_node(node_id, tree_data, output_html, output_pdf)

        print(f"\n✓ 节点视图已生成:")
        print(f"   HTML: {output_html}")
        print(f"   PDF: {output_pdf}")

    workflow.close()


def demo_search(tree_data):
    """演示搜索功能"""
    print("\n" + "=" * 70)
    print("演示 5: 搜索 - 在文档中搜索并展示位置")
    print("=" * 70)

    pdf_path = "data/pdfs/2403.14123v1_origin.pdf"
    mineru_dir = "data/pdfs/res/2403.14123v1_origin"

    workflow = PDFToTreeWorkflow(pdf_path, mineru_dir)

    # 搜索
    query = "Arithmetic Intensity"
    output_html = "results/demo_search_results.html"

    results = workflow.search_and_view(query, tree_data, output_html)

    print(f"\n🔍 搜索 '{query}' 找到 {len(results)} 个结果")
    print(f"   结果页面: {output_html}")

    workflow.close()


def main():
    """运行所有演示"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "MinerU 集成功能演示" + " " * 29 + "║")
    print("╚" + "═" * 68 + "╝")

    # 演示 1: 基础工作流
    tree_data = demo_basic_workflow()

    # 演示 2: 解析器
    demo_parser()

    # 演示 3: PDF 查看器
    demo_pdf_viewer()

    # 演示 4: 节点定位
    demo_node_location(tree_data)

    # 演示 5: 搜索
    demo_search(tree_data)

    # 总结
    print("\n" + "=" * 70)
    print("📁 生成的文件")
    print("=" * 70)
    files = [
        "results/demo_output.json",
        "results/demo_page_preview.html",
        "results/demo_node_view.html",
        "results/demo_node_highlighted.pdf",
        "results/demo_search_results.html"
    ]
    for f in files:
        exists = "✓" if Path(f).exists() else "✗"
        print(f"  {exists} {f}")

    print("\n" + "=" * 70)
    print("💡 提示")
    print("=" * 70)
    print("  1. 在浏览器中打开 .html 文件查看可视化结果")
    print("  2. 使用 PDF 阅读器打开 .pdf 文件查看高亮效果")
    print("  3. 查看 .json 文件了解完整的数据结构")
    print("=" * 70)


if __name__ == "__main__":
    main()
