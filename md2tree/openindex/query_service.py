"""
查询服务

实现核心的两阶段查询流程：
1. Query + 树结构 → LLM → 选择节点
2. Query + 节点原文 → LLM → 生成答案
"""

import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict, Any, Optional

from .document_store import DocumentStore
from .models import (
    QueryResponse, SelectedNode, NodeLocation, BlockLocation,
    SearchResponse, SearchResult
)

# 导入 md2tree 模块 - 使用相对导入
from ..llm import LLMConfig, call_llm
from ..core.tree import find_node_by_id, structure_to_list
from ..parsers.middle_json import MiddleJSONParser
from ..parsers.mineru import MinerUParser, create_pdf_link
from ..core.config import get_config_value

logger = logging.getLogger(__name__)


class QueryService:
    """查询服务"""

    def __init__(self, document_store: DocumentStore, max_cache_size: int = None):
        """
        初始化查询服务

        Args:
            document_store: 文档存储实例
            max_cache_size: 最大缓存大小，如果为 None 则从配置读取
        """
        self.store = document_store
        self.config = LLMConfig()
        # 使用 LRU 缓存，限制最大大小，避免内存无限增长
        if max_cache_size is None:
            max_cache_size = get_config_value('app', 'parser_cache_size', 50)
        self._max_cache_size = max_cache_size
        self._parser_cache: OrderedDict[str, Any] = OrderedDict()

    def _get_parser(self, doc_id: str, parser_type: str) -> Optional[Any]:
        """
        获取解析器实例（带 LRU 缓存）
        
        Args:
            doc_id: 文档 ID
            parser_type: 解析器类型 ('middle' 或 'mineru')
            
        Returns:
            解析器实例，如果不存在则返回 None
        """
        cache_key = f"{doc_id}_{parser_type}"
        
        # 检查缓存
        if cache_key in self._parser_cache:
            # 移动到末尾（LRU）
            self._parser_cache.move_to_end(cache_key)
            return self._parser_cache[cache_key]
        
        # 创建新解析器
        mineru_dir = self.store.get_mineru_output_dir(doc_id)
        if not mineru_dir:
            return None
        
        parser = None
        if parser_type == 'middle':
            files = list(mineru_dir.glob("**/vlm/*_middle.json"))
            if files:
                parser = MiddleJSONParser(str(files[0]))
        elif parser_type == 'mineru':
            files = list(mineru_dir.glob("**/vlm/*_content_list*.json"))
            if files:
                parser = MinerUParser(str(files[0]))
        
        if parser:
            # 检查缓存大小，移除最旧的项
            if len(self._parser_cache) >= self._max_cache_size:
                oldest_key = next(iter(self._parser_cache))
                del self._parser_cache[oldest_key]
                logger.debug(f"Removed oldest parser from cache: {oldest_key}")
            
            self._parser_cache[cache_key] = parser
        
        return parser

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计字典
        """
        return {
            "size": len(self._parser_cache),
            "max_size": self._max_cache_size,
            "keys": list(self._parser_cache.keys())
        }
    
    def clear_parser_cache(self, doc_id: str = None) -> None:
        """
        清除解析器缓存
        
        Args:
            doc_id: 要清除的文档 ID，如果为 None 则清除所有缓存
        """
        if doc_id:
            keys_to_remove = [k for k in self._parser_cache if k.startswith(doc_id)]
            for k in keys_to_remove:
                del self._parser_cache[k]
            logger.info(f"Cleared parser cache for document {doc_id}")
        else:
            self._parser_cache.clear()
            logger.info("Cleared all parser cache")

    def query(
        self, 
        doc_id: str, 
        query: str, 
        top_k: int = 5,
        conversation_id: Optional[str] = None,
        save_to_conversation: bool = True
    ) -> QueryResponse:
        """
        执行查询

        Args:
            doc_id: 文档 ID
            query: 查询文本
            top_k: 返回节点数量
            conversation_id: 可选的对话 ID，用于获取历史上下文
            save_to_conversation: 是否自动保存消息到对话

        Returns:
            查询响应
        """
        # 1. 获取树结构
        tree_data = self.store.load_tree(doc_id)
        if not tree_data:
            raise ValueError(f"Document {doc_id} not found or not parsed")

        structure = tree_data['structure']
        doc = self.store.get_document(doc_id)
        
        # 1.5 获取对话历史（如果提供了 conversation_id）
        chat_history = []
        if conversation_id:
            conv = self.store.get_conversation(conversation_id)
            if conv and conv.get('messages'):
                # 只保留最近 N 条消息作为上下文（从配置读取）
                max_history = get_config_value('query', 'max_history_messages', 10)
                for msg in conv['messages'][-max_history:]:
                    chat_history.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })

        # 2. 第一阶段：选择相关节点
        selected_nodes = self._select_nodes(query, structure, top_k)

        # 3. 获取节点原文
        node_contents = []
        for node_info in selected_nodes:
            node = find_node_by_id(structure, node_info.node_id)
            if node:
                node_contents.append({
                    'node_id': node_info.node_id,
                    'title': node.get('title', ''),
                    'text': node.get('text', '')
                })

        # 4. 第二阶段：生成答案（带对话历史）
        answer = self._generate_answer(query, node_contents, chat_history)

        # 5. 获取位置信息
        locations = self._get_node_locations(selected_nodes, structure, doc)

        # 6. 构建源信息
        sources = []
        for node_info, location in zip(selected_nodes, locations):
            node = find_node_by_id(structure, node_info.node_id)
            if node:
                # 从配置读取预览长度
                preview_length = get_config_value('query', 'text_preview_length', 200)
                text_preview = node.get('text', '')
                if text_preview and len(text_preview) > preview_length:
                    text_preview = text_preview[:preview_length] + '...'
                
                sources.append({
                    'node_id': node_info.node_id,
                    'title': node.get('title', ''),
                    'text_preview': text_preview,
                    'page_range': location.page_range
                })

        response = QueryResponse(
            query=query,
            answer=answer,
            selected_nodes=selected_nodes,
            locations=locations,
            sources=sources
        )

        # 7. 保存消息到对话（服务层负责）
        if conversation_id and save_to_conversation:
            self._save_to_conversation(conversation_id, query, response)

        return response

    def _save_to_conversation(
        self, 
        conversation_id: str, 
        query: str, 
        response: QueryResponse
    ) -> None:
        """
        保存查询和回答到对话

        Args:
            conversation_id: 对话 ID
            query: 用户查询
            response: 查询响应
        """
        try:
            # 保存用户问题
            self.store.add_message(
                conversation_id=conversation_id,
                role='user',
                content=query
            )
            # 保存 AI 回答
            self.store.add_message(
                conversation_id=conversation_id,
                role='assistant',
                content=response.answer,
                references=response.sources,
                selected_nodes=[n.model_dump() for n in response.selected_nodes],
                locations=[loc.model_dump() for loc in response.locations]
            )
        except Exception as e:
            logger.error(f"Failed to save messages to conversation {conversation_id}: {e}")

    def _select_nodes(self, query: str, structure: List[Dict], top_k: int) -> List[SelectedNode]:
        """
        第一阶段：选择相关节点

        Args:
            query: 查询文本
            structure: 树结构
            top_k: 返回数量

        Returns:
            选中的节点列表
        """
        # 构建树结构的简化表示（只包含标题和摘要）
        tree_repr = self._build_tree_repr(structure)

        prompt = f"""你是一个学术论文阅读助手。给定一个用户查询和论文的结构，请选择最相关的章节。

## 用户查询
{query}

## 论文结构
{tree_repr}

## 任务
请选择与查询最相关的 {top_k} 个章节，返回JSON格式：
```json
{{
    "selected": [
        {{"node_id": "0001", "reason": "选择理由"}},
        ...
    ]
}}
```

只返回JSON，不要其他内容。"""

        response = call_llm(prompt, self.config)

        # 解析响应
        try:
            # 提取 JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())
            selected = data.get('selected', [])

            return [
                SelectedNode(
                    node_id=item['node_id'],
                    title=self._get_node_title(structure, item['node_id']),
                    reason=item.get('reason', '')
                )
                for item in selected[:top_k]
            ]
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            # 降级方案：返回前 top_k 个节点
            all_nodes = structure_to_list(structure)
            return [
                SelectedNode(
                    node_id=node.get('node_id', ''),
                    title=node.get('title', ''),
                    reason='fallback'
                )
                for node in all_nodes[:top_k]
                if node.get('node_id')
            ]

    def _generate_answer(
        self, 
        query: str, 
        node_contents: List[Dict],
        chat_history: List[Dict] = None
    ) -> str:
        """
        第二阶段：基于节点原文生成答案

        Args:
            query: 查询文本
            node_contents: 节点内容列表
            chat_history: 对话历史（可选）

        Returns:
            生成的答案
        """
        # 构建上下文
        context_parts = []
        for content in node_contents:
            context_parts.append(f"## {content['title']}\n{content['text']}")

        context = "\n\n".join(context_parts)

        # 构建系统提示
        system_prompt = f"""你是一个学术论文阅读助手。基于以下论文内容回答用户的问题。

## 论文内容
{context}

## 任务
请基于论文内容准确回答用户的问题。如果论文内容不足以回答问题，请说明。回答应该简洁、准确、有依据。
如果用户的问题涉及到之前对话中提到的内容（如"它"、"这个"等代词），请结合对话历史理解用户意图。
"""

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史
        if chat_history:
            messages.extend(chat_history)
        
        # 添加当前问题
        messages.append({"role": "user", "content": query})

        return call_llm(query, self.config, chat_history=messages[:-1] if len(messages) > 1 else None)

    def _build_tree_repr(self, structure: List[Dict], indent: int = 0) -> str:
        """构建树结构的文本表示"""
        lines = []
        for node in structure:
            prefix = "  " * indent
            node_id = node.get('node_id', '')
            title = node.get('title', '')
            summary = node.get('summary', node.get('prefix_summary', ''))

            # 从配置读取预览长度
            summary_preview_length = get_config_value('query', 'summary_preview_length', 100)
            
            if summary:
                if len(summary) > summary_preview_length:
                    summary = summary[:summary_preview_length] + '...'
                lines.append(f"{prefix}- [{node_id}] {title}: {summary}")
            else:
                # 使用文本的前N字符作为预览
                text_preview = node.get('text', '')
                if text_preview:
                    if len(text_preview) > summary_preview_length:
                        text_preview = text_preview[:summary_preview_length] + '...'
                else:
                    text_preview = ''
                lines.append(f"{prefix}- [{node_id}] {title}: {text_preview}")

            if node.get('nodes'):
                lines.append(self._build_tree_repr(node['nodes'], indent + 1))

        return '\n'.join(lines)

    def _get_node_title(self, structure: List[Dict], node_id: str) -> str:
        """获取节点标题"""
        node = find_node_by_id(structure, node_id)
        return node.get('title', '') if node else ''

    def _get_node_locations(
        self,
        selected_nodes: List[SelectedNode],
        structure: List[Dict],
        doc
    ) -> List[NodeLocation]:
        """获取节点位置信息"""
        locations = []

        for node_info in selected_nodes:
            node = find_node_by_id(structure, node_info.node_id)
            if not node:
                locations.append(NodeLocation(
                    node_id=node_info.node_id,
                    title=node_info.title
                ))
                continue

            page_info = node.get('page_info', {})
            page_range = page_info.get('page_range')
            title_block_data = page_info.get('title_block')
            content_blocks_data = page_info.get('content_blocks', [])

            # 构建标题块位置
            title_block = None
            if title_block_data:
                title_block = BlockLocation(
                    page_idx=title_block_data.get('page_idx', 0),
                    page_num=title_block_data.get('page_idx', 0) + 1,
                    bbox=title_block_data.get('bbox', [0, 0, 0, 0]),
                    type=title_block_data.get('type', 'title')
                )

            # 构建内容块位置
            content_blocks = [
                BlockLocation(
                    page_idx=b.get('page_idx', 0),
                    page_num=b.get('page_idx', 0) + 1,
                    bbox=b.get('bbox', [0, 0, 0, 0]),
                    type=b.get('type', 'text')
                )
                for b in content_blocks_data[:5]  # 限制数量
            ]

            locations.append(NodeLocation(
                node_id=node_info.node_id,
                title=node.get('title', ''),
                page_range=list(page_range) if page_range else None,
                title_block=title_block,
                content_blocks=content_blocks
            ))

        return locations

    def search_blocks(self, doc_id: str, query: str, max_results: int = 10) -> SearchResponse:
        """
        直接搜索文本块

        Args:
            doc_id: 文档 ID
            query: 搜索文本
            max_results: 最大结果数

        Returns:
            搜索响应
        """
        tree_data = self.store.load_tree(doc_id)
        if not tree_data:
            raise ValueError(f"Document {doc_id} not found")

        doc = self.store.get_document(doc_id)
        doc_pdf_path = doc.get('pdf_path', '') if doc else ''

        results = []

        # 尝试使用缓存的 middle.json 解析器
        parser = self._get_parser(doc_id, 'middle')
        
        if parser:
            # 使用 middle.json 进行精确搜索
            raw_results = parser.search_and_locate(query)

            for i, result in enumerate(raw_results[:max_results]):
                results.append(SearchResult(
                    rank=i + 1,
                    page_num=result['page_idx'] + 1,
                    bbox=result['bbox'],
                    type=result['type'],
                    context=result['context'],
                    pdf_link=create_pdf_link(
                        doc_pdf_path,
                        result['page_idx'],
                        result['bbox']
                    )
                ))
        else:
            # 降级到缓存的 content_list.json 解析器
            parser = self._get_parser(doc_id, 'mineru')
            if parser:
                raw_results = parser.find_text_location(query, fuzzy=True)

                for i, result in enumerate(raw_results[:max_results]):
                    results.append(SearchResult(
                        rank=i + 1,
                        page_num=result['page_idx'] + 1,
                        bbox=result['bbox'],
                        type=result.get('type', 'text'),
                        context=result.get('text', '')[:150],
                        pdf_link=create_pdf_link(
                            doc_pdf_path,
                            result['page_idx'],
                            result['bbox']
                        )
                    ))

        return SearchResponse(
            query=query,
            total_results=len(results),
            results=results
        )
