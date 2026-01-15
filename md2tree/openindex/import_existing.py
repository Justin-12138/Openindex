"""
导入已有的 MinerU 解析结果

用于快速测试和导入已经解析好的 PDF 文档。
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

from .document_store import DocumentStore
from .models import DocumentStatus
from ..core.converter import md_to_tree
from ..parsers.middle_json import add_middlejson_location_to_tree
from ..parsers.mineru import add_location_info_to_tree
from ..core.tree import get_tree_stats


def import_existing_document(
    pdf_path: str,
    mineru_output_dir: str,
    data_dir: str = None
):
    """
    导入已有的文档和解析结果

    Args:
        pdf_path: PDF 文件路径
        mineru_output_dir: MinerU 输出目录
        data_dir: 数据目录（默认使用 openindex/data）
    """
    if data_dir is None:
        data_dir = str(Path(__file__).parent / "data")

    store = DocumentStore(data_dir)

    pdf_path = Path(pdf_path)
    mineru_dir = Path(mineru_output_dir)

    # 检查文件是否存在
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # 查找 vlm 输出目录
    vlm_dirs = list(mineru_dir.glob("**/vlm"))
    if not vlm_dirs:
        raise FileNotFoundError(f"VLM output not found in {mineru_dir}")

    vlm_dir = vlm_dirs[0]

    # 查找 markdown 文件
    md_files = list(vlm_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"Markdown not found in {vlm_dir}")

    md_path = md_files[0]

    # 查找 middle.json
    middle_files = list(vlm_dir.glob("*_middle.json"))
    middle_path = middle_files[0] if middle_files else None

    # 查找 content_list.json
    content_list_files = list(vlm_dir.glob("*_content_list*.json"))
    content_list_path = content_list_files[0] if content_list_files else None

    print(f"PDF: {pdf_path}")
    print(f"Markdown: {md_path}")
    print(f"Middle JSON: {middle_path}")
    print(f"Content List: {content_list_path}")

    # 创建文档记录
    with open(pdf_path, 'rb') as f:
        content = f.read()

    doc = store.add_document(pdf_path.name, content)
    doc_id = doc.id

    print(f"\nCreated document: {doc_id}")

    # 复制 MinerU 输出到数据目录
    target_mineru_dir = store.parsed_dir / doc_id / pdf_path.stem / "vlm"
    target_mineru_dir.mkdir(parents=True, exist_ok=True)

    # 复制所有文件
    for src_file in vlm_dir.iterdir():
        if src_file.is_file():
            shutil.copy(src_file, target_mineru_dir / src_file.name)
        elif src_file.is_dir():
            shutil.copytree(src_file, target_mineru_dir / src_file.name, dirs_exist_ok=True)

    print(f"Copied MinerU output to: {target_mineru_dir.parent}")

    # 更新文档的 mineru_dir
    store.update_document_status(
        doc_id,
        DocumentStatus.PARSING,
        mineru_dir=str(target_mineru_dir.parent)
    )

    # 转换 Markdown 为树结构
    print("\nConverting Markdown to tree...")
    tree_data = md_to_tree(
        str(md_path),
        add_node_id=True,
        keep_text=True
    )

    # 添加位置信息
    if middle_path:
        print("Adding location info from middle.json...")
        tree_data['structure'] = add_middlejson_location_to_tree(
            tree_data['structure'],
            str(middle_path)
        )
        tree_data['location_source'] = 'middle.json'
    elif content_list_path:
        print("Adding location info from content_list.json...")
        tree_data['structure'] = add_location_info_to_tree(
            tree_data['structure'],
            str(content_list_path),
            pdf_path=str(pdf_path)
        )
        tree_data['location_source'] = 'content_list.json'

    # 添加元数据
    tree_data['doc_id'] = doc_id
    tree_data['pdf_path'] = str(store.uploads_dir / f"{doc_id}_{pdf_path.stem}.pdf")
    tree_data['stats'] = get_tree_stats(tree_data['structure'])

    # 保存树结构
    store.save_tree(doc_id, tree_data)

    # 更新状态为就绪
    store.update_document_status(
        doc_id,
        DocumentStatus.READY,
        tree_structure=tree_data['structure'],
        stats=tree_data['stats']
    )

    print(f"\n✓ Document imported successfully!")
    print(f"  ID: {doc_id}")
    print(f"  Name: {doc.name}")
    print(f"  Nodes: {tree_data['stats']['total_nodes']}")
    print(f"  Max depth: {tree_data['stats']['max_depth']}")

    return doc_id


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Import existing MinerU parsed document')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('mineru_dir', help='MinerU output directory')
    parser.add_argument('--data-dir', help='Data directory (default: openindex/data)')

    args = parser.parse_args()

    doc_id = import_existing_document(
        args.pdf_path,
        args.mineru_dir,
        args.data_dir
    )

    print(f"\nYou can now query this document using doc_id: {doc_id}")


if __name__ == "__main__":
    main()
