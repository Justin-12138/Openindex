"""
树剪枝模块

提供将小节点合并到父节点的功能，以降低树的复杂度。
"""

import logging
from typing import List, Dict, Any, Optional

from .client import count_tokens, LLMConfig

logger = logging.getLogger(__name__)


def update_node_token_counts(
    node_list: List[Dict[str, Any]],
    model: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    更新每个节点的总 token 数（包括所有后代）
    
    Args:
        node_list: 包含 'level' 和 'text' 字段的节点列表
        model: 用于 token 计数的模型名称
        
    Returns:
        添加了 'text_token_count' 字段的更新节点列表
    """
    def find_all_descendants(
        parent_index: int,
        parent_level: int,
        nodes: List[Dict[str, Any]]
    ) -> List[int]:
        """查找所有后代节点的索引"""
        descendants = []
        for i in range(parent_index + 1, len(nodes)):
            current_level = nodes[i]['level']
            if current_level <= parent_level:
                break
            descendants.append(i)
        return descendants

    result = node_list.copy()

    # 从后往前处理（子节点优先于父节点）
    for i in range(len(result) - 1, -1, -1):
        node = result[i]
        level = node['level']

        # 获取所有后代
        descendants = find_all_descendants(i, level, result)

        # 合并节点和所有后代的文本
        total_text = node.get('text', '')
        for child_idx in descendants:
            child_text = result[child_idx].get('text', '')
            if child_text:
                total_text += '\n' + child_text

        result[i]['text_token_count'] = count_tokens(total_text, model=model or "glm-4.7")

    return result


def thin_tree_by_token_count(
    node_list: List[Dict[str, Any]],
    min_token_threshold: int,
    model: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    通过将小节点合并到父节点来剪枝树
    
    如果节点的总 token 数（包括后代）低于阈值，
    则所有子节点将合并到该节点，子节点被移除。
    
    Args:
        node_list: 包含 'level'、'text' 和 'text_token_count' 的节点列表
        min_token_threshold: 保持节点独立的最小 token 数
        model: 用于 token 计数的模型名称
        
    Returns:
        剪枝后的节点列表
    """
    def find_all_descendants(
        parent_index: int,
        parent_level: int,
        nodes: List[Dict[str, Any]]
    ) -> List[int]:
        """查找所有后代节点的索引"""
        descendants = []
        for i in range(parent_index + 1, len(nodes)):
            current_level = nodes[i]['level']
            if current_level <= parent_level:
                break
            descendants.append(i)
        return descendants

    result = node_list.copy()
    nodes_to_remove = set()

    # 从后往前处理
    for i in range(len(result) - 1, -1, -1):
        if i in nodes_to_remove:
            continue

        node = result[i]
        level = node['level']
        total_tokens = node.get('text_token_count', 0)

        # 如果节点太小，将子节点合并到其中
        if total_tokens < min_token_threshold:
            descendants = find_all_descendants(i, level, result)

            # 收集子节点的文本
            children_texts = []
            for child_idx in sorted(descendants):
                if child_idx not in nodes_to_remove:
                    child_text = result[child_idx].get('text', '')
                    if child_text.strip():
                        children_texts.append(child_text)
                    nodes_to_remove.add(child_idx)

            # 合并文本
            if children_texts:
                parent_text = node.get('text', '')
                merged_text = parent_text
                for child_text in children_texts:
                    if merged_text and not merged_text.endswith('\n'):
                        merged_text += '\n\n'
                    merged_text += child_text

                result[i]['text'] = merged_text
                result[i]['text_token_count'] = count_tokens(merged_text, model=model or "glm-4.7")

    # 移除标记的节点
    for index in sorted(nodes_to_remove, reverse=True):
        result.pop(index)

    return result


def apply_thinning(
    node_list: List[Dict[str, Any]],
    min_token_threshold: int = 5000,
    model: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    应用树剪枝：添加 token 计数，然后合并小节点
    
    Args:
        node_list: 包含 'level' 和 'text' 字段的节点列表
        min_token_threshold: 保持节点独立的最小 token 数
        model: 用于 token 计数的模型名称
        
    Returns:
        剪枝后的节点列表
    """
    # 首先添加 token 计数
    with_counts = update_node_token_counts(node_list, model=model)

    # 然后应用剪枝
    thinned = thin_tree_by_token_count(
        with_counts,
        min_token_threshold=min_token_threshold,
        model=model
    )

    logger.info(f"剪枝: {len(node_list)} -> {len(thinned)} 个节点")

    return thinned
