"""
文档检索测试 - 基于 md2tree 树结构的智能检索

本测试实现了类似 PageIndex cookbook/chat.py 的核心逻辑：
1. 从树结构中移除原文，只保留标题和摘要
2. 让 LLM 根据问题返回相关节点 ID 列表
3. 验证返回的 JSON 格式
4. 根据节点 ID 获取原文内容
5. 生成最终答案
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# 使用相对导入
from md2tree.llm import LLMConfig, call_llm, call_llm_async
from md2tree.core.converter import md_to_tree, print_toc
from md2tree.core.tree import (
    get_tree_stats,
    find_node_by_id,
    structure_to_list,
)


# ============================================================================
# 工具函数 (类似 pageindex/utils.py)
# ============================================================================

def remove_fields(data: Any, fields: List[str] = ['text']) -> Any:
    """
    从树结构中递归删除指定字段。

    Args:
        data: 树结构数据
        fields: 要删除的字段列表

    Returns:
        删除指定字段后的树结构
    """
    if isinstance(data, dict):
        return {k: remove_fields(v, fields)
                for k, v in data.items() if k not in fields}
    elif isinstance(data, list):
        return [remove_fields(item, fields) for item in data]
    return data


def create_node_mapping(tree: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    创建节点 ID 到节点的映射。

    Args:
        tree: 树结构

    Returns:
        字典，key 是 node_id，value 是对应的节点
    """
    node_map = {}

    def traverse(nodes):
        if isinstance(nodes, dict):
            node_id = nodes.get('node_id')
            if node_id:
                node_map[node_id] = nodes
            if 'nodes' in nodes:
                traverse(nodes['nodes'])
        elif isinstance(nodes, list):
            for node in nodes:
                traverse(node)

    traverse(tree)
    return node_map


def extract_json(content: str) -> Dict[str, Any]:
    """
    从 LLM 返回内容中提取 JSON。

    支持 ```json ... ``` 格式和纯 JSON 格式。

    Args:
        content: LLM 返回的内容

    Returns:
        解析后的 JSON 对象，失败返回空字典
    """
    try:
        # 首先尝试提取 ```json ... ``` 中的内容
        start_idx = content.find("```json")
        if start_idx != -1:
            start_idx += 7  # 跳过 ```json
            end_idx = content.rfind("```")
            json_content = content[start_idx:end_idx].strip()
        else:
            # 如果没有分隔符，假设整个内容是 JSON
            json_content = content.strip()

        # 清理可能导致解析错误的问题
        json_content = json_content.replace('None', 'null')  # Python None -> JSON null
        json_content = json_content.replace('\n', ' ').replace('\r', ' ')  # 移除换行
        json_content = ' '.join(json_content.split())  # 标准化空白符

        # 尝试解析并返回 JSON 对象
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"[警告] JSON 解析失败: {e}")
        # 尝试进一步清理
        try:
            # 移除闭合括号前的尾随逗号
            json_content = json_content.replace(',]', ']').replace(',}', '}')
            return json.loads(json_content)
        except Exception:
            print(f"[错误] 清理后仍无法解析 JSON")
            return {}
    except Exception as e:
        print(f"[错误] 提取 JSON 时发生意外错误: {e}")
        return {}


def validate_json_response(response: Dict[str, Any]) -> bool:
    """
    验证 LLM 返回的 JSON 响应格式。

    预期格式: {"thinking": str, "node_list": List[str]}

    Args:
        response: 解析后的 JSON 对象

    Returns:
        是否格式正确
    """
    if not isinstance(response, dict):
        print("[验证失败] 响应不是字典类型")
        return False

    if 'node_list' not in response:
        print("[验证失败] 响应缺少 'node_list' 字段")
        return False

    if not isinstance(response['node_list'], list):
        print("[验证失败] 'node_list' 不是列表类型")
        return False

    if 'thinking' not in response:
        print("[警告] 响应缺少 'thinking' 字段（非必需）")

    return True


def print_wrapped(text: str, width: int = 80):
    """
    打印包装的文本（自动换行）。

    Args:
        text: 要打印的文本
        width: 每行最大宽度
    """
    import textwrap
    wrapped = textwrap.fill(text, width=width)
    print(wrapped)


# ============================================================================
# 检索核心逻辑
# ============================================================================

async def tree_search(
    tree: List[Dict[str, Any]],
    query: str,
    config: Any = None
) -> Dict[str, Any]:
    """
    基于树结构的智能检索。

    1. 移除树结构中的原文
    2. 让 LLM 返回相关节点 ID
    3. 验证 JSON 格式
    4. 返回检索结果

    Args:
        tree: 完整的树结构（包含 text 和 summary）
        query: 用户查询
        config: LLM 配置

    Returns:
        检索结果，包含 thinking, node_list, retrieved_content
    """
    if config is None:
        config = LLMConfig()

    # 1. 移除原文，只保留标题、摘要等信息
    tree_without_text = remove_fields(tree.copy(), fields=['text'])

    # 2. 构建搜索提示词
    search_prompt = f"""
你是一个文档检索助手。你的任务是根据用户问题，从文档树结构中找出所有可能包含答案的节点。

文档树结构如下（每个节点包含节点ID、标题和摘要）：
{json.dumps(tree_without_text, indent=2, ensure_ascii=False)}

用户问题：{query}

请分析问题并返回相关节点的ID列表。请严格按照以下JSON格式回复：
{{
    "thinking": "<你的思考过程，分析哪些节点与问题相关>",
    "node_list": ["node_id_1", "node_id_2", "node_id_3"]
}}

注意：
- 只返回node_id列表，不要返回节点内容
- node_list中的ID必须存在于上述树结构中
- 直接返回JSON格式，不要包含其他内容
"""

    print("\n" + "=" * 70)
    print("🔍 调用 LLM 进行树搜索...")
    print("=" * 70)

    # 3. 调用 LLM
    llm_response = await call_llm_async(search_prompt, config)

    # 4. 提取和验证 JSON
    print("\n📋 LLM 原始响应:")
    print("-" * 70)
    print(llm_response[:500] + "..." if len(llm_response) > 500 else llm_response)
    print("-" * 70)

    search_result = extract_json(llm_response)

    # 5. 验证格式
    if not validate_json_response(search_result):
        print("\n❌ JSON 格式验证失败！")
        return {
            "thinking": "JSON 格式错误",
            "node_list": [],
            "error": "Invalid JSON format"
        }

    # 6. 打印思考过程
    if search_result.get('thinking'):
        print("\n🤔 LLM 思考过程:")
        print("-" * 70)
        print_wrapped(search_result['thinking'])
        print("-" * 70)

    # 7. 打印检索到的节点
    node_map = create_node_mapping(tree)
    retrieved_nodes = search_result.get('node_list', [])

    print(f"\n📌 检索到 {len(retrieved_nodes)} 个相关节点:")
    for node_id in retrieved_nodes:
        node = node_map.get(node_id)
        if node:
            print(f"  - [{node_id}] {node.get('title', 'Unknown')}")
        else:
            print(f"  - [{node_id}] <节点不存在>")

    # 8. 获取原文内容
    relevant_content = "\n\n---\n\n".join([
        node_map[node_id].get('text', '')
        for node_id in retrieved_nodes
        if node_id in node_map
    ])

    return {
        "thinking": search_result.get('thinking', ''),
        "node_list": retrieved_nodes,
        "retrieved_content": relevant_content,
        "node_map": node_map,
        "llm_response": llm_response
    }


async def answer_question(
    query: str,
    context: str,
    config: Any = None
) -> str:
    """
    基于检索到的上下文回答问题。

    Args:
        query: 用户问题
        context: 检索到的相关文档内容
        config: LLM 配置

    Returns:
        生成的答案
    """
    if config is None:
        config = LLMConfig()

    answer_prompt = f"""
基于以下文档内容回答用户问题。

文档内容：
{context}

用户问题：{query}

请提供详细、准确的答案。如果文档中没有相关信息，请明确说明。
"""

    print("\n" + "=" * 70)
    print("💬 生成答案...")
    print("=" * 70)

    answer = await call_llm_async(answer_prompt, config)

    return answer


async def rag_pipeline(
    tree: List[Dict[str, Any]],
    query: str,
    config: Any = None,
    show_content: bool = True
) -> Dict[str, Any]:
    """
    完整的 RAG (Retrieval-Augmented Generation) 流程。

    Args:
        tree: 文档树结构
        query: 用户查询
        config: LLM 配置
        show_content: 是否显示检索到的内容

    Returns:
        包含检索和生成结果的字典
    """
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + " " * 20 + "文档检索测试 RAG Pipeline" + " " * 21 + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    print(f"\n❓ 用户问题: {query}")

    # Step 1: 检索相关节点
    search_result = await tree_search(tree, query, config)

    if search_result.get('error'):
        return search_result

    # Step 2: 显示检索到的内容（可选）
    if show_content and search_result['retrieved_content']:
        content_preview = search_result['retrieved_content']
        if len(content_preview) > 1000:
            content_preview = content_preview[:1000] + "\n\n... (内容已截断，共 " + str(len(search_result['retrieved_content'])) + " 字符)"
        print("\n📄 检索到的内容预览:")
        print("-" * 70)
        print(content_preview)
        print("-" * 70)

    # Step 3: 生成答案
    answer = await answer_question(query, search_result['retrieved_content'], config)

    print("\n✅ 生成的答案:")
    print("-" * 70)
    print_wrapped(answer)
    print("-" * 70)

    return {
        "query": query,
        "search_result": search_result,
        "answer": answer
    }


# ============================================================================
# 测试查询生成
# ============================================================================

def generate_test_queries() -> List[Dict[str, str]]:
    """
    生成多样化的测试查询。

    包括：
    - 深度查询：需要深入理解某个具体概念
    - 广度查询：需要综合多个章节的信息
    - 总结性查询：需要整体概括
    - 细节性查询：询问具体数值或指标
    - 对比性查询：需要对比不同概念

    Returns:
        查询列表，每个查询包含类型和问题
    """
    return [
        {
            "type": "深度查询",
            "query": "什么是 'memory wall'（内存墙）问题？请详细解释其成因和影响。",
            "description": "需要深入理解内存墙这个核心概念"
        },
        {
            "type": "广度查询",
            "query": "文档中提到了哪些解决方案来克服内存墙问题？请列举并简要说明。",
            "description": "需要覆盖多个章节（训练算法、部署策略、硬件设计）"
        },
        {
            "type": "总结性查询",
            "query": "这篇论文的主要结论是什么？",
            "description": "需要整体把握文章的核心观点"
        },
        {
            "type": "细节性查询",
            "query": "过去20年中，服务器硬件峰值 FLOPS、DRAM 带宽和互连带宽的增长倍数分别是多少？",
            "description": "需要找到具体的数值指标"
        },
        {
            "type": "对比性查询",
            "query": "Transformer 编码器模型（如 BERT）和解码器模型（如 GPT）在推理时有什么性能差异？原因是什么？",
            "description": "需要对比两种架构的算术强度和延迟"
        }
    ]


# ============================================================================
# 主测试函数
# ============================================================================

async def run_retrieval_test():
    """
    运行完整的检索测试。
    """
    # 加载配置
    config = llm.LLMConfig()
    print(f"\n🔧 LLM 配置: {config}")

    # 加载树结构
    tree_path = Path(__file__).parent.parent / "results" / "test2_structure.json"
    print(f"\n📂 加载树结构: {tree_path}")

    with open(tree_path, 'r', encoding='utf-8') as f:
        tree_data = json.load(f)

    tree = tree_data['structure']
    doc_name = tree_data.get('doc_name', 'unknown')
    doc_description = tree_data.get('doc_description', '')

    print(f"\n📖 文档名称: {doc_name}")
    print(f"📝 文档描述: {doc_description}")

    # 打印文档目录
    print("\n📚 文档目录:")
    print("-" * 70)
    print_toc(tree)
    print("-" * 70)

    # 获取树统计信息
    stats = get_tree_stats(tree)
    print(f"\n📊 树结构统计:")
    print(f"  - 总节点数: {stats['total_nodes']}")
    print(f"  - 最大深度: {stats['max_depth']}")
    print(f"  - 叶子节点数: {stats['leaf_nodes']}")

    # 生成测试查询
    queries = generate_test_queries()

    print("\n" + "=" * 70)
    print("🎯 测试查询列表")
    print("=" * 70)
    for i, q in enumerate(queries, 1):
        print(f"{i}. [{q['type']}] {q['query']}")
        print(f"   说明: {q['description']}")
        print()

    # 运行每个查询
    results = []
    for i, query_info in enumerate(queries, 1):
        print("\n\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 25 + f"查询 {i}/{len(queries)}" + " " * 28 + "║")
        print("╚" + "═" * 68 + "╝")

        result = await rag_pipeline(
            tree=tree,
            query=query_info['query'],
            config=config,
            show_content=False  # 不显示完整内容以保持输出简洁
        )

        result['query_type'] = query_info['type']
        result['query_description'] = query_info['description']
        results.append(result)

    # 打印总结
    print("\n\n")
    print("█" * 70)
    print("█" + " " * 25 + "测试完成" + " " * 30 + "█")
    print("█" * 70)

    print("\n📊 检索结果汇总:")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        query_type = result.get('query_type', 'Unknown')
        node_count = len(result.get('search_result', {}).get('node_list', []))
        answer_length = len(result.get('answer', ''))
        print(f"{i}. [{query_type}] 检索到 {node_count} 个节点，答案长度: {answer_length} 字符")
    print("-" * 70)

    return results


if __name__ == "__main__":
    asyncio.run(run_retrieval_test())
