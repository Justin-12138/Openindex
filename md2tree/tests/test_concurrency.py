"""
md2tree 并发控制测试脚本

演示 config.toml 文件如何控制并发 LLM 请求。
"""

import asyncio
import sys
from pathlib import Path

# 使用相对导入
from md2tree.core.config import load_config, get_config_value
from md2tree.llm import LLMConfig, get_semaphore, reset_semaphore
from md2tree.core.converter import md_to_tree, md_to_tree_async
from md2tree.core.tree import get_tree_stats


def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("测试 1: 配置加载")
    print("=" * 60)

    # 加载配置
    config = load_config()

    print("\n从 config.toml 加载的配置:")
    print("-" * 40)

    # 打印 LLM 配置
    llm_config = config.get('llm', {})
    print(f"[llm]")
    print(f"  model: {llm_config.get('model', 'N/A')}")
    print(f"  max_concurrent_requests: {llm_config.get('max_concurrent_requests', 'N/A')}")
    print(f"  request_timeout: {llm_config.get('request_timeout', 'N/A')}")
    print(f"  max_retries: {llm_config.get('max_retries', 'N/A')}")
    print(f"  retry_delay: {llm_config.get('retry_delay', 'N/A')}")

    # 打印剪枝配置
    thinning_config = config.get('thinning', {})
    print(f"\n[thinning]")
    print(f"  enabled: {thinning_config.get('enabled', 'N/A')}")
    print(f"  min_token_threshold: {thinning_config.get('min_token_threshold', 'N/A')}")

    # 打印摘要配置
    summary_config = config.get('summary', {})
    print(f"\n[summary]")
    print(f"  enabled: {summary_config.get('enabled', 'N/A')}")
    print(f"  summary_token_threshold: {summary_config.get('summary_token_threshold', 'N/A')}")

    print("\n✓ 配置加载成功")


def test_config_value_access():
    """测试配置值访问"""
    print("\n" + "=" * 60)
    print("测试 2: 配置值访问")
    print("=" * 60)

    # 测试获取单个值
    model = get_config_value('llm', 'model', 'default_model')
    max_concurrent = get_config_value('llm', 'max_concurrent_requests', 5)
    timeout = get_config_value('llm', 'request_timeout', 120)

    print(f"模型: {model}")
    print(f"最大并发请求数: {max_concurrent}")
    print(f"请求超时: {timeout}s")

    print("\n✓ 配置值访问成功")


def test_llm_config_with_toml():
    """测试使用 TOML 设置的 LLMConfig 类"""
    print("\n" + "=" * 60)
    print("测试 3: 使用 TOML 设置的 LLMConfig")
    print("=" * 60)

    # 创建 LLMConfig（将从 TOML 加载）
    from md2tree.llm import LLMConfig
    config = LLMConfig()

    print(f"LLMConfig 已创建:")
    print(f"  model: {config.model}")
    print(f"  api_base: {config.api_base}")
    print(f"  max_retries: {config.max_retries}")
    print(f"  retry_delay: {config.retry_delay}")

    print("\n✓ LLMConfig 创建成功")


async def test_semaphore_creation():
    """测试用于并发控制的信号量创建"""
    print("\n" + "=" * 60)
    print("测试 4: 并发控制信号量")
    print("=" * 60)

    # 先重置信号量
    reset_semaphore()

    # 获取信号量（将基于配置创建）
    semaphore = get_semaphore()

    # 从配置获取最大并发值
    max_concurrent = get_config_value('llm', 'max_concurrent_requests', 5)

    print(f"信号量已创建，max_concurrent={max_concurrent}")
    print(f"信号量内部计数器: {semaphore._value}")

    # 测试获取/释放信号量
    print("\n测试信号量获取/释放...")
    async with semaphore:
        print(f"  获取信号量，剩余: {semaphore._value}")

    print(f"  释放信号量，剩余: {semaphore._value}")

    print("\n✓ 信号量测试成功")


async def test_concurrent_limit_simulation():
    """模拟带信号量控制的并发请求"""
    print("\n" + "=" * 60)
    print("测试 5: 并发请求模拟")
    print("=" * 60)

    # 重置信号量
    reset_semaphore()

    # 从配置获取最大并发数
    max_concurrent = get_config_value('llm', 'max_concurrent_requests', 5)
    print(f"配置中的最大并发请求数: {max_concurrent}")

    # 模拟并发任务
    semaphore = get_semaphore()
    active_count = 0
    max_active = 0

    async def simulated_request(task_id: int, duration: float = 0.1):
        """模拟 LLM 请求"""
        nonlocal active_count, max_active

        async with semaphore:
            active_count += 1
            max_active = max(max_active, active_count)
            print(f"  任务 {task_id}: 已启动 (活动: {active_count})")
            await asyncio.sleep(duration)
            active_count -= 1
            print(f"  任务 {task_id}: 已完成 (活动: {active_count})")

    # 创建超过 max_concurrent 的任务数
    num_tasks = max_concurrent * 2
    print(f"\n启动 {num_tasks} 个任务，max_concurrent={max_concurrent}...")

    tasks = [simulated_request(i, 0.05) for i in range(num_tasks)]
    await asyncio.gather(*tasks)

    print(f"\n最大活动并发任务数: {max_active}")
    print(f"预期最大值（来自配置）: {max_concurrent}")

    if max_active <= max_concurrent:
        print("✓ 并发控制正常工作!")
    else:
        print("✗ 并发控制可能未正常工作")

    print("\n✓ 并发请求模拟完成")


def test_basic_conversion():
    """测试基本的 Markdown 到树转换"""
    import pytest
    import tempfile
    from pathlib import Path
    
    print("\n" + "=" * 60)
    print("测试 6: 带配置的基本转换")
    print("=" * 60)

    # 创建临时 Markdown 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Title 1

Content for title 1.

## Subtitle 1.1

Content for subtitle 1.1.

## Subtitle 1.2

Content for subtitle 1.2.

# Title 2

Content for title 2.
""")
        temp_md = f.name
    
    try:
        result = md_to_tree(temp_md)

        stats = get_tree_stats(result['structure'])
        print(f"文档: {result['doc_name']}")
        print(f"总节点数: {stats['total_nodes']}")
        print(f"最大深度: {stats['max_depth']}")

        print("\n✓ 基本转换成功")
    finally:
        # 清理临时文件
        Path(temp_md).unlink(missing_ok=True)


async def test_thinning_with_config():
    """测试使用配置设置的树剪枝"""
    import tempfile
    from pathlib import Path
    
    print("\n" + "=" * 60)
    print("测试 7: 使用配置设置的树剪枝")
    print("=" * 60)

    # 从配置获取剪枝阈值
    threshold = get_config_value('thinning', 'min_token_threshold', 5000)
    print(f"配置中的剪枝阈值: {threshold}")

    # 使用较低的阈值进行测试
    test_threshold = 100
    print(f"使用测试阈值: {test_threshold}")

    # 创建临时 Markdown 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Title 1

Content for title 1 with some text.

## Subtitle 1.1

Content for subtitle 1.1 with more text.

## Subtitle 1.2

Content for subtitle 1.2.

# Title 2

Content for title 2 with additional text.
""")
        temp_md = f.name
    
    try:
        config = LLMConfig()
        result = await md_to_tree_async(
            temp_md,
            config=config,
            enable_thinning=True,  # 修复参数名：if_thinning -> enable_thinning
            thinning_threshold=test_threshold,
        )

        stats = get_tree_stats(result['structure'])
        print(f"剪枝后的总节点数: {stats['total_nodes']}")

        print("\n✓ 使用配置的树剪枝成功")
    finally:
        # 清理临时文件
        Path(temp_md).unlink(missing_ok=True)


def main():
    """运行所有测试"""
    print("md2tree 并发控制测试")
    print("=" * 60)

    # 同步测试
    test_config_loading()
    test_config_value_access()
    test_llm_config_with_toml()
    test_basic_conversion()

    # 异步测试
    print("\n" + "=" * 60)
    print("运行异步测试...")
    print("=" * 60)

    asyncio.run(test_semaphore_creation())
    asyncio.run(test_concurrent_limit_simulation())
    asyncio.run(test_thinning_with_config())

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)

    # 显示配置文件位置
    config_path = Path(__file__).parent / "config.toml"
    print(f"\n配置文件位置: {config_path}")
    print("\n要调整并发，请编辑 config.toml 中的 max_concurrent_requests")


if __name__ == "__main__":
    main()
