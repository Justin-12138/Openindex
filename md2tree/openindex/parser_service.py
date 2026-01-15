"""
PDF 解析服务

调用 MinerU 解析 PDF，并生成树结构。
"""

import subprocess
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .document_store import DocumentStore
from .models import DocumentStatus

# 导入 md2tree 模块 - 使用相对导入
from ..core.converter import md_to_tree
from ..parsers.middle_json import add_middlejson_location_to_tree
from ..parsers.mineru import add_location_info_to_tree
from ..core.tree import get_tree_stats
from ..llm import load_config, get_config_value

logger = logging.getLogger(__name__)


class ParserService:
    """PDF 解析服务"""

    def __init__(self, document_store: DocumentStore):
        """
        初始化解析服务

        Args:
            document_store: 文档存储实例
        """
        self.store = document_store

        # 加载配置
        load_config()
        # server_url 和 api_url 支持从环境变量读取（MINERU_SERVER_URL, MINERU_API_URL）
        self.mineru_server = get_config_value('mineru', 'server_url', 'http://101.52.216.165:30909')
        self.mineru_api_url = get_config_value('mineru', 'api_url', self.mineru_server)  # 默认使用 server_url
        self.mineru_backend = get_config_value('mineru', 'backend', 'vlm-http-client')
        self.mineru_executable = get_config_value('mineru', 'executable', 'mineru')
        self.mineru_extra_args = get_config_value('mineru', 'extra_args', [])

    async def parse_document(self, doc_id: str) -> Dict[str, Any]:
        """
        解析文档

        Args:
            doc_id: 文档 ID

        Returns:
            解析结果
        """
        doc = self.store.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # 使用字典访问方式
        doc_status = doc.get('status', 'pending')
        doc_pdf_path = doc.get('pdf_path', '')
        doc_name = doc.get('name', '')

        if doc_status == 'ready':
            # 已解析，直接返回树结构
            tree_data = self.store.load_tree(doc_id)
            if tree_data:
                return tree_data

        # 更新状态为解析中
        self.store.update_document_status(doc_id, DocumentStatus.PARSING)

        try:
            # 1. 创建新解析版本
            latest_version = self.store.db.get_latest_parse_version(doc_id)
            next_version = (latest_version['version'] + 1) if latest_version else 1
            parse_version = self.store.db.create_parse_version(
                doc_id,
                version=next_version,
                status='parsing_mineru'
            )
            
            # 2. 调用 MinerU 解析 PDF
            self.store.update_document_status(doc_id, DocumentStatus.PARSING_MINERU)
            output_dir = self.store.get_mineru_output_dir_for_new_version(doc_id)
            await self._run_mineru(doc_pdf_path, output_dir)
            
            # 更新版本的 mineru_dir
            self.store.db.update_parse_version(
                doc_id,
                next_version,
                mineru_dir=str(output_dir)
            )

            # 2. 查找 MinerU 输出文件
            mineru_output = self._find_mineru_output(output_dir, doc_name)

            # MinerU 目录已在创建版本时更新

            # 3. 转换 Markdown 为树结构
            self.store.update_document_status(doc_id, DocumentStatus.PARSING_MARKDOWN)
            tree_data = md_to_tree(
                str(mineru_output['md_path']),
                add_node_id=True,
                keep_text=True
            )

            # 4. 添加位置信息
            self.store.update_document_status(doc_id, DocumentStatus.ADDING_LOCATIONS)
            if mineru_output.get('middle_json_path'):
                tree_data['structure'] = add_middlejson_location_to_tree(
                    tree_data['structure'],
                    str(mineru_output['middle_json_path'])
                )
                tree_data['location_source'] = 'middle.json'
            elif mineru_output.get('content_list_path'):
                tree_data['structure'] = add_location_info_to_tree(
                    tree_data['structure'],
                    str(mineru_output['content_list_path']),
                    pdf_path=doc_pdf_path
                )
                tree_data['location_source'] = 'content_list.json'

            # 5. 添加元数据
            tree_data['doc_id'] = doc_id
            tree_data['pdf_path'] = doc_pdf_path
            tree_data['stats'] = get_tree_stats(tree_data['structure'])

            # 6. 保存树结构（使用当前版本）
            self.store.save_tree(doc_id, tree_data, version=next_version)

            # 7. 更新状态为完成
            self.store.update_document_status(
                doc_id,
                DocumentStatus.READY,
                tree_structure=tree_data['structure'],
                stats=tree_data['stats']
            )

            return tree_data

        except Exception as e:
            import traceback
            error_message = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"Parse failed for {doc_id}: {error_message}\n{error_traceback}")
            
            # 更新文档状态
            self.store.update_document_status(
                doc_id,
                DocumentStatus.ERROR,
                error_message=f"{error_message}\n\n{error_traceback}"
            )
            raise RuntimeError(f"Parse failed: {error_message}") from e

    def _build_mineru_command(self, pdf_path: str, output_dir: Path) -> list:
        """
        构建 MinerU 命令行
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
            
        Returns:
            命令行参数列表
        """
        cmd = [
            self.mineru_executable,
            "-p", pdf_path,
            "-b", self.mineru_backend,
            "-u", self.mineru_server,
            "-o", str(output_dir)
        ]
        
        # 添加额外参数
        if self.mineru_extra_args:
            cmd.extend(self.mineru_extra_args)
        
        return cmd

    async def _run_mineru(self, pdf_path: str, output_dir: Path):
        """
        运行 MinerU 解析

        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = self._build_mineru_command(pdf_path, output_dir)

        logger.info(f"Running MinerU: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"MinerU failed: {error_msg}")

        logger.info(f"MinerU completed: {stdout.decode()}")

    def _find_mineru_output(self, output_dir: Path, doc_name: str) -> Dict[str, Any]:
        """
        查找 MinerU 输出文件

        Args:
            output_dir: 输出目录
            doc_name: 文档名称

        Returns:
            输出文件路径字典
        """
        result = {}

        # MinerU 输出格式：output_dir/doc_name/vlm/
        # 或直接在 output_dir/vlm/

        # 尝试查找 vlm 目录
        vlm_dirs = list(output_dir.glob("**/vlm"))
        if not vlm_dirs:
            raise FileNotFoundError(f"MinerU vlm output not found in {output_dir}")

        vlm_dir = vlm_dirs[0]
        result['dir'] = vlm_dir.parent

        # 查找 markdown 文件
        md_files = list(vlm_dir.glob("*.md"))
        if md_files:
            result['md_path'] = md_files[0]
        else:
            raise FileNotFoundError(f"Markdown file not found in {vlm_dir}")

        # 查找 middle.json（推荐）
        middle_files = list(vlm_dir.glob("*_middle.json"))
        if middle_files:
            result['middle_json_path'] = middle_files[0]

        # 查找 content_list.json（备用）
        content_list_files = list(vlm_dir.glob("*_content_list*.json"))
        if content_list_files:
            # 优先使用 v2 版本
            v2_files = [f for f in content_list_files if 'v2' in f.name]
            result['content_list_path'] = v2_files[0] if v2_files else content_list_files[0]

        return result

    def get_tree(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取树结构"""
        return self.store.load_tree(doc_id)
