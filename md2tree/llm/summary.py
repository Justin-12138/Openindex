"""
摘要生成模块

提供使用 LLM 生成节点摘要和文档描述的功能。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from .client import call_llm, call_llm_async, call_llm_async_batch, count_tokens, LLMConfig

logger = logging.getLogger(__name__)


async def generate_node_summary(
    node: Dict[str, Any],
    config: Optional[LLMConfig] = None
) -> str:
    """
    为单个节点生成摘要
    
    Args:
        node: 包含 'text' 字段的节点字典
        config: LLM 配置
        
    Returns:
        生成的摘要文本
    """
    prompt = f"""You are given a part of a document, your task is to generate a description of the partial document about what are main points covered in the partial document.

Partial Document Text: {node['text']}

Directly return the description, do not include any other text."""

    return await call_llm_async(prompt, config)


async def get_node_summary(
    node: Dict[str, Any],
    summary_token_threshold: int = 200,
    config: Optional[LLMConfig] = None
) -> str:
    """
    获取节点摘要，如果文本足够短则使用原文
    
    Args:
        node: 包含 'text' 字段的节点字典
        summary_token_threshold: 使用原文的 token 阈值
        config: LLM 配置
        
    Returns:
        摘要文本（原文或生成的）
    """
    node_text = node.get('text', '')
    num_tokens = count_tokens(node_text, model=config.model if config else "glm-4.7")

    if num_tokens < summary_token_threshold:
        return node_text
    else:
        return await generate_node_summary(node, config)


async def generate_summaries_for_structure(
    structure: List[Dict[str, Any]],
    summary_token_threshold: int = 200,
    config: Optional[LLMConfig] = None
) -> List[Dict[str, Any]]:
    """
    为结构中的所有节点生成摘要
    
    叶子节点获得 'summary'，父节点获得 'prefix_summary'。
    
    Args:
        structure: 树结构
        summary_token_threshold: 使用原文的 token 阈值
        config: LLM 配置
        
    Returns:
        添加了摘要的更新结构
    """
    def is_leaf(node: Dict[str, Any]) -> bool:
        return not node.get('nodes')

    def structure_to_list(structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将结构展平为节点列表"""
        nodes = []
        if isinstance(structure, dict):
            nodes.append(structure)
            if 'nodes' in structure:
                nodes.extend(structure_to_list(structure['nodes']))
        elif isinstance(structure, list):
            for item in structure:
                nodes.extend(structure_to_list(item))
        return nodes

    # 获取所有节点
    nodes = structure_to_list(structure)

    # 并行为所有节点生成摘要
    tasks = [
        get_node_summary(node, summary_token_threshold, config)
        for node in nodes
    ]
    summaries = await asyncio.gather(*tasks)

    # 将摘要分配给节点
    for node, summary in zip(nodes, summaries):
        if is_leaf(node):
            node['summary'] = summary
        else:
            node['prefix_summary'] = summary

    return structure


def generate_doc_description(
    structure: List[Dict[str, Any]],
    config: Optional[LLMConfig] = None
) -> str:
    """
    从树结构生成文档描述
    
    Args:
        structure: 树结构（建议使用清理后的，不含 'text' 字段）
        config: LLM 配置
        
    Returns:
        文档描述
    """
    prompt = f"""You are an expert in generating descriptions for a document.
You are given a structure of a document. Your task is to generate a one-sentence description for the document, which makes it easy to distinguish the document from other documents.

Document Structure: {structure}

Directly return the description, do not include any other text."""

    return call_llm(prompt, config)


def create_clean_structure_for_description(structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为文档描述生成创建清理后的结构
    
    只包含 title、node_id、summary 和 prefix_summary 字段。
    
    Args:
        structure: 树结构
        
    Returns:
        清理后的结构
    """
    if isinstance(structure, dict):
        clean_node = {}
        for key in ['title', 'node_id', 'summary', 'prefix_summary']:
            if key in structure:
                clean_node[key] = structure[key]

        if 'nodes' in structure and structure['nodes']:
            clean_node['nodes'] = create_clean_structure_for_description(structure['nodes'])

        return clean_node
    elif isinstance(structure, list):
        return [create_clean_structure_for_description(item) for item in structure]
    else:
        return structure


async def generate_doc_description_async(
    structure: List[Dict[str, Any]],
    config: Optional[LLMConfig] = None
) -> str:
    """
    异步版本的文档描述生成
    
    Args:
        structure: 树结构
        config: LLM 配置
        
    Returns:
        文档描述
    """
    clean_structure = create_clean_structure_for_description(structure)

    prompt = f"""You are an expert in generating descriptions for a document.
You are given a structure of a document. Your task is to generate a one-sentence description for the document, which makes it easy to distinguish the document from other documents.

Document Structure: {clean_structure}

Directly return the description, do not include any other text."""

    return await call_llm_async(prompt, config)
