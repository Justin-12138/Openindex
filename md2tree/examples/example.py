"""
md2tree 模块使用示例

本脚本演示 md2tree 包的各种使用方式。
"""

from md2tree import (
    md_to_tree,
    save_tree,
    print_toc,
)
from md2tree.utils import (
    get_tree_stats,
    find_node_by_id,
    find_node_by_title,
    structure_to_list,
    get_leaf_nodes,
    pretty_print_tree,
    validate_tree,
)


def example_basic_usage():
    """基础用法示例"""
    print("=" * 60)
    print("示例 1: 基础用法")
    print("=" * 60)

    # 将 Markdown 文件转换为树结构
    tree_data = md_to_tree('example.md')

    # 打印文档名称
    print(f"文档: {tree_data['doc_name']}")

    # 打印目录
    print("\n目录:")
    print_toc(tree_data['structure'])

    # 保存到文件
    save_tree(tree_data, 'example_output.json')


def example_with_options():
    """带选项的示例"""
    print("\n" + "=" * 60)
    print("示例 2: 带选项")
    print("=" * 60)

    # 不添加节点 ID，不保留文本内容
    tree_data = md_to_tree(
        md_path='example.md',
        add_node_id=False,
        keep_text=False
    )

    print(f"文档: {tree_data['doc_name']}")
    print("\n精简树 (无 ID，无文本):")
    print_toc(tree_data['structure'])


def example_tree_stats():
    """树结构统计示例"""
    print("\n" + "=" * 60)
    print("示例 3: 树结构统计")
    print("=" * 60)

    tree_data = md_to_tree('example.md')

    # 获取统计信息
    stats = get_tree_stats(tree_data['structure'])

    print(f"总节点数: {stats['total_nodes']}")
    print(f"最大深度: {stats['max_depth']}")
    print(f"叶子节点: {stats['leaf_nodes']}")
    print(f"内部节点: {stats['internal_nodes']}")


def example_find_nodes():
    """查找节点示例"""
    print("\n" + "=" * 60)
    print("示例 4: 查找节点")
    print("=" * 60)

    tree_data = md_to_tree('example.md')

    # 按标题查找节点
    node = find_node_by_title(tree_data['structure'], 'Introduction')
    if node:
        print(f"找到 'Introduction':")
        print(f"  - ID: {node.get('node_id')}")
        print(f"  - 行号: {node.get('line_num')}")

    # 按 ID 查找节点
    node = find_node_by_id(tree_data['structure'], '0001')
    if node:
        print(f"\n找到节点 '0001':")
        print(f"  - 标题: {node.get('title')}")


def example_node_lists():
    """节点列表操作示例"""
    print("\n" + "=" * 60)
    print("示例 5: 节点列表操作")
    print("=" * 60)

    tree_data = md_to_tree('example.md')

    # 获取所有节点的扁平列表
    all_nodes = structure_to_list(tree_data['structure'])
    print(f"总节点数: {len(all_nodes)}")

    # 获取叶子节点
    leaf_nodes = get_leaf_nodes(tree_data['structure'])
    print(f"叶子节点数: {len(leaf_nodes)}")

    print("\n叶子节点标题:")
    for node in leaf_nodes:
        print(f"  - {node.get('title')}")


def example_validation():
    """树结构验证示例"""
    print("\n" + "=" * 60)
    print("示例 6: 树结构验证")
    print("=" * 60)

    tree_data = md_to_tree('example.md')

    # 验证树结构
    issues = validate_tree(tree_data['structure'])

    if issues:
        print("发现验证问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("树结构验证通过!")


def example_pretty_print():
    """美化打印示例"""
    print("\n" + "=" * 60)
    print("示例 7: 美化打印")
    print("=" * 60)

    tree_data = md_to_tree('example.md')

    # 美化打印，显示文本预览
    pretty_print_tree(tree_data['structure'], max_text_length=30)


def example_custom_fields():
    """自定义字段示例"""
    print("\n" + "=" * 60)
    print("示例 8: 自定义字段")
    print("=" * 60)

    # 只保留 title 和 line_num
    tree_data = md_to_tree(
        md_path='example.md',
        keep_fields=['title', 'line_num', 'nodes']
    )

    pretty_print_tree(tree_data['structure'])


if __name__ == "__main__":
    # 运行所有示例（假设 example.md 文件存在）
    try:
        example_basic_usage()
        example_with_options()
        example_tree_stats()
        example_find_nodes()
        example_node_lists()
        example_validation()
        example_pretty_print()
        example_custom_fields()
    except FileNotFoundError:
        print("请创建 'example.md' 文件以运行示例。")
        print("\n你可以创建如下内容:")
        print("""
# 我的文档

## 简介

这是简介部分。

## 第一章

### 第 1.1 节

这里是一些内容。

### 第 1.2 节

更多内容。

## 结论

结束。
        """)
