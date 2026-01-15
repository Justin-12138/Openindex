"""
md2tree 模块测试脚本

演示不需要 LLM API 访问的基本功能。
"""

import asyncio
import sys
from pathlib import Path

# 从本地模块导入
import md2tree
import utils

# 从模块获取函数
md_to_tree = md2tree.md_to_tree
save_tree = md2tree.save_tree
print_toc = md2tree.print_toc
pretty_print_tree = utils.pretty_print_tree
validate_tree = utils.validate_tree
get_tree_stats = utils.get_tree_stats


def test_basic_conversion():
    """测试基本的 Markdown 到树转换"""
    print("=" * 60)
    print("测试 1: 基本转换")
    print("=" * 60)

    result = md_to_tree('example.md')

    print(f"文档: {result['doc_name']}")
    print("\n目录:")
    print_toc(result['structure'])

    save_tree(result, 'results/test_basic.json')
    print("\n✓ 基本转换成功")


def test_without_text():
    """测试不包含文本内容的转换"""
    print("\n" + "=" * 60)
    print("测试 2: 不包含文本内容")
    print("=" * 60)

    result = md_to_tree('example.md', keep_text=False)

    print(f"文档: {result['doc_name']}")
    print("\n精简树 (无文本):")
    print_toc(result['structure'])

    save_tree(result, 'results/test_no_text.json')
    print("\n✓ 不包含文本的转换成功")


def test_without_node_id():
    """测试不包含节点 ID 的转换"""
    print("\n" + "=" * 60)
    print("测试 3: 不包含节点 ID")
    print("=" * 60)

    result = md_to_tree('example.md', add_node_id=False)

    print(f"文档: {result['doc_name']}")
    print("\n不包含节点 ID 的树:")
    print_toc(result['structure'])

    save_tree(result, 'results/test_no_id.json')
    print("\n✓ 不包含节点 ID 的转换成功")


def test_tree_stats():
    """测试树结构统计"""
    print("\n" + "=" * 60)
    print("测试 4: 树结构统计")
    print("=" * 60)

    result = md_to_tree('example.md')

    stats = get_tree_stats(result['structure'])
    print(f"总节点数: {stats['total_nodes']}")
    print(f"最大深度: {stats['max_depth']}")
    print(f"叶子节点: {stats['leaf_nodes']}")
    print(f"内部节点: {stats['internal_nodes']}")

    print("\n✓ 统计计算成功")


def test_validation():
    """测试树结构验证"""
    print("\n" + "=" * 60)
    print("测试 5: 树结构验证")
    print("=" * 60)

    result = md_to_tree('example.md')

    issues = validate_tree(result['structure'])
    if issues:
        print("验证问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("未发现验证问题 - 树结构有效!")

    print("\n✓ 验证成功")


def test_pretty_print():
    """测试美化打印功能"""
    print("\n" + "=" * 60)
    print("测试 6: 美化打印")
    print("=" * 60)

    result = md_to_tree('example.md')

    pretty_print_tree(result['structure'], max_text_length=30)

    print("\n✓ 美化打印成功")


async def test_with_thinning():
    """测试树剪枝（需要 tiktoken）"""
    print("\n" + "=" * 60)
    print("测试 7: 树剪枝")
    print("=" * 60)

    try:
        # 从本地模块导入
        import llm
        import thinning
        import summary

        config = llm.LLMConfig()  # 使用 .env 配置

        result = await md2tree.md_to_tree_async(
            'example.md',
            config=config,
            if_thinning=True,
            thinning_threshold=100,  # 用于测试的低阈值
            if_add_node_summary=False,
            if_add_doc_description=False,
        )

        print(f"文档: {result['doc_name']}")
        print("\n剪枝后的树:")
        print_toc(result['structure'])

        stats = get_tree_stats(result['structure'])
        print(f"\n剪枝后的总节点数: {stats['total_nodes']}")

        save_tree(result, 'results/test_thinned.json')
        print("\n✓ 树剪枝成功")
    except Exception as e:
        print(f"✗ 树剪枝失败: {e}")


async def test_with_summaries():
    """测试摘要生成（需要 LLM API）"""
    print("\n" + "=" * 60)
    print("测试 8: 摘要生成 (需要 LLM API)")
    print("=" * 60)

    try:
        # 从本地模块导入
        import llm

        config = llm.LLMConfig()  # 使用 .env 配置

        result = await md2tree.md_to_tree_async(
            'example.md',
            config=config,
            if_thinning=False,
            if_add_node_summary=True,
            summary_token_threshold=50,  # 用于触发 LLM 的低阈值
            if_add_doc_description=True,
        )

        print(f"文档: {result['doc_name']}")

        if result.get('doc_description'):
            print(f"\n文档描述: {result['doc_description']}")

        print("\n带摘要的树:")
        print_toc(result['structure'])

        save_tree(result, 'results/test_summaries.json')
        print("\n✓ 摘要生成成功")
    except Exception as e:
        print(f"✗ 摘要生成失败: {e}")
        print("  (如果 LLM API 未配置，这是预期的)")


def main():
    """运行所有测试"""
    # 运行基本测试（不需要 LLM）
    test_basic_conversion()
    test_without_text()
    test_without_node_id()
    test_tree_stats()
    test_validation()
    test_pretty_print()

    # 运行高级测试（可能需要 LLM）
    print("\n" + "=" * 60)
    print("运行高级测试...")
    print("=" * 60)

    asyncio.run(test_with_thinning())
    asyncio.run(test_with_summaries())

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
