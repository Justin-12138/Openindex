"""
文档存储服务

使用 SQLite3 管理文档元数据，文件存储在本地文件系统。
"""

import json
import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .database import get_database, Database
from .models import DocumentStatus

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的安全文件名
    """
    # 只保留字母、数字、下划线、连字符、点和中文字符
    name = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', filename)
    # 移除连续的下划线
    name = re.sub(r'_+', '_', name)
    # 移除首尾的下划线和点
    name = name.strip('_.')
    # 限制长度（从配置读取，但这里使用较小的值，因为文件名会加上 doc_id 前缀）
    from ..core.config import get_config_value
    max_length = get_config_value('app', 'max_filename_length', 255)
    # 考虑到 doc_id 前缀（8字符 + 1下划线），实际文件名限制更小
    safe_length = min(100, max_length - 10)  # 保留空间给前缀
    if len(name) > safe_length:
        name = name[:safe_length]
    return name or 'unnamed'


class DocumentStore:
    """文档存储管理器"""

    def __init__(self, data_dir: str):
        """
        初始化文档存储

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.uploads_dir = self.data_dir / "uploads"
        self.parsed_dir = self.data_dir / "parsed"
        self.trees_dir = self.data_dir / "trees"

        # 创建目录
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.trees_dir.mkdir(parents=True, exist_ok=True)

        # 获取数据库实例
        self.db: Database = get_database(data_dir)

    # ============= 文档管理 =============

    def add_document(self, filename: str, content: bytes) -> Dict[str, Any]:
        """
        添加新文档

        Args:
            filename: 原始文件名
            content: 文件内容

        Returns:
            文档信息
        """
        doc_id = str(uuid.uuid4())[:8]
        # 清理文件名，移除不安全字符
        name = sanitize_filename(Path(filename).stem)

        # 准备文件路径
        pdf_filename = f"{doc_id}_{name}.pdf"
        pdf_path = self.uploads_dir / pdf_filename
        
        try:
            # 1. 先写数据库（可回滚）
            doc = self.db.add_document(
                doc_id=doc_id,
                name=name,
                original_filename=filename,
                pdf_path=str(pdf_path),
                file_size=len(content)
            )
            
            # 2. 再写文件
            pdf_path.write_bytes(content)
            logger.info(f"Saved PDF file: {pdf_path}")
            
            return self._format_document(doc)
            
        except Exception as e:
            # 清理可能写入的文件
            if pdf_path.exists():
                try:
                    pdf_path.unlink()
                    logger.warning(f"Cleaned up orphaned file: {pdf_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup orphaned file {pdf_path}: {cleanup_error}")
            # 数据库会自动回滚（在 get_connection 的 except 块中）
            raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        doc = self.db.get_document(doc_id)
        if doc:
            return self._format_document(doc)
        return None

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """获取所有文档"""
        docs = self.db.get_all_documents()
        return [self._format_document(doc) for doc in docs]

    def update_document_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        md_path: str = None,
        mineru_dir: str = None,
        tree_structure: Dict = None,
        stats: Dict = None,
        error_message: str = None
    ) -> bool:
        """更新文档状态"""
        status_value = status.value if isinstance(status, DocumentStatus) else status
        
        return self.db.update_document_status(
            doc_id=doc_id,
            status=status_value,
            md_path=md_path,
            mineru_dir=mineru_dir,
            total_nodes=stats.get('total_nodes', 0) if stats else None,
            max_depth=stats.get('max_depth', 0) if stats else None,
            error_message=error_message
        )

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档及所有相关文件
        
        删除内容：
        - PDF 原文件
        - MD 文件（如果存在）
        - 树结构 JSON 文件
        - MinerU 解析输出目录（包含 middle.json、content_list.json、images 等）
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            是否删除成功
        """
        doc = self.db.get_document(doc_id)
        if not doc:
            logger.warning(f"Document {doc_id} not found in database")
            return False

        deleted_files = []
        errors = []

        # 1. 删除 PDF 文件
        if doc.get('pdf_path'):
            pdf_path = Path(doc['pdf_path'])
            if pdf_path.exists():
                try:
                    pdf_path.unlink()
                    deleted_files.append(f"PDF: {pdf_path}")
                except Exception as e:
                    errors.append(f"Failed to delete PDF {pdf_path}: {e}")

        # 2. 删除 MD 文件（如果单独存储）
        if doc.get('md_path'):
            md_path = Path(doc['md_path'])
            if md_path.exists():
                try:
                    md_path.unlink()
                    deleted_files.append(f"MD: {md_path}")
                except Exception as e:
                    errors.append(f"Failed to delete MD {md_path}: {e}")

        # 3. 删除树结构 JSON 文件
        if doc.get('tree_path'):
            tree_path = Path(doc['tree_path'])
            if tree_path.exists():
                try:
                    tree_path.unlink()
                    deleted_files.append(f"Tree: {tree_path}")
                except Exception as e:
                    errors.append(f"Failed to delete tree {tree_path}: {e}")
        
        # 同时检查默认位置的树文件
        default_tree_path = self.trees_dir / f"{doc_id}_tree.json"
        if default_tree_path.exists() and str(default_tree_path) != doc.get('tree_path'):
            try:
                default_tree_path.unlink()
                deleted_files.append(f"Tree (default): {default_tree_path}")
            except Exception as e:
                errors.append(f"Failed to delete default tree {default_tree_path}: {e}")

        # 4. 删除 MinerU 解析输出目录（包含 MD、middle.json、images 等）
        # 首先检查数据库中记录的 mineru_dir
        if doc.get('mineru_dir'):
            mineru_dir = Path(doc['mineru_dir'])
            if mineru_dir.exists():
                try:
                    shutil.rmtree(mineru_dir)
                    deleted_files.append(f"MinerU dir: {mineru_dir}")
                except Exception as e:
                    errors.append(f"Failed to delete mineru dir {mineru_dir}: {e}")
        
        # 同时检查默认位置的解析目录
        parsed_doc_dir = self.parsed_dir / doc_id
        if parsed_doc_dir.exists():
            try:
                shutil.rmtree(parsed_doc_dir)
                deleted_files.append(f"Parsed dir: {parsed_doc_dir}")
            except Exception as e:
                errors.append(f"Failed to delete parsed dir {parsed_doc_dir}: {e}")

        # 记录日志
        if deleted_files:
            logger.info(f"Deleted files for document {doc_id}: {', '.join(deleted_files)}")
        if errors:
            for error in errors:
                logger.error(error)

        # 5. 从数据库删除（会级联删除对话和消息）
        db_deleted = self.db.delete_document(doc_id)
        if db_deleted:
            logger.info(f"Document {doc_id} deleted from database")
        else:
            logger.error(f"Failed to delete document {doc_id} from database")

        return db_deleted

    def get_mineru_output_dir(self, doc_id: str, version: int = None) -> Optional[Path]:
        """
        获取 MinerU 输出目录
        
        Args:
            doc_id: 文档 ID
            version: 版本号（如果为 None，则使用最新版本）
            
        Returns:
            MinerU 输出目录路径
        """
        # 如果有版本管理，优先从版本表获取
        parse_version = self.db.get_parse_version(doc_id, version)
        if parse_version and parse_version.get('mineru_dir'):
            return Path(parse_version['mineru_dir'])
        
        # 兼容旧数据：从文档表获取
        doc = self.db.get_document(doc_id)
        if doc and doc.get('mineru_dir'):
            return Path(doc['mineru_dir'])

        # 默认位置
        parsed_doc_dir = self.parsed_dir / doc_id
        if parsed_doc_dir.exists():
            return parsed_doc_dir
        return None

    def get_mineru_output_dir_for_new_version(self, doc_id: str) -> Path:
        """
        获取新版本的 MinerU 输出目录（创建版本化目录）
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            新版本的 MinerU 输出目录路径
        """
        # 获取下一个版本号
        latest_version = self.db.get_latest_parse_version(doc_id)
        next_version = (latest_version['version'] + 1) if latest_version else 1
        
        # 创建版本化目录
        versioned_dir = self.parsed_dir / doc_id / f"v{next_version}"
        versioned_dir.mkdir(parents=True, exist_ok=True)
        
        return versioned_dir

    # ============= 树结构管理 =============

    def save_tree(self, doc_id: str, tree_data: Dict[str, Any], version: int = None) -> str:
        """
        保存树结构
        
        Args:
            doc_id: 文档 ID
            tree_data: 树结构数据
            version: 版本号（如果为 None，则使用最新版本或创建新版本）
            
        Returns:
            树结构文件路径
        """
        # 如果没有指定版本，获取或创建最新版本
        if version is None:
            latest_version = self.db.get_latest_parse_version(doc_id)
            if latest_version:
                version = latest_version['version']
            else:
                # 创建新版本
                version_info = self.db.create_parse_version(doc_id, status='ready')
                version = version_info['version'] if version_info else 1
        
        # 使用版本化的文件名
        tree_path = self.trees_dir / f"{doc_id}_v{version}_tree.json"
        try:
            # 确保目录存在
            tree_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(tree_path, 'w', encoding='utf-8') as f:
                json.dump(tree_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved tree structure to {tree_path}")
        except (IOError, OSError) as e:
            logger.error(f"Failed to save tree structure to {tree_path}: {e}")
            raise RuntimeError(f"Failed to save tree structure: {e}") from e

        # 更新数据库（同时更新文档表和版本表）
        try:
            stats = tree_data.get('stats', {})
            # 更新版本表
            self.db.update_parse_version(
                doc_id,
                version,
                tree_path=str(tree_path),
                status='ready',
                total_nodes=stats.get('total_nodes', 0),
                max_depth=stats.get('max_depth', 0)
            )
            # 更新文档表（保持兼容性，指向最新版本）
            self.db.update_document(
                doc_id,
                tree_path=str(tree_path),
                total_nodes=stats.get('total_nodes', 0),
                max_depth=stats.get('max_depth', 0)
            )
        except Exception as e:
            logger.error(f"Failed to update database for tree path: {e}")
            # 不抛出异常，文件已保存成功

        return str(tree_path)

    def load_tree(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """加载树结构"""
        doc = self.db.get_document(doc_id)
        if not doc:
            return None

        tree_path = doc.get('tree_path')
        if tree_path:
            path = Path(tree_path)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (IOError, OSError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to load tree from {path}: {e}")
                    # 继续尝试旧路径

        # 兼容旧路径
        legacy_path = self.trees_dir / f"{doc_id}_tree.json"
        if legacy_path.exists():
            try:
                with open(legacy_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (IOError, OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load tree from legacy path {legacy_path}: {e}")

        return None

    # ============= 对话管理 =============

    def create_conversation(self, doc_id: str, title: str = None) -> Dict[str, Any]:
        """创建新对话"""
        return self.db.create_conversation(doc_id, title)

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """获取对话"""
        return self.db.get_conversation(conv_id)

    def get_conversations(self, doc_id: str) -> List[Dict[str, Any]]:
        """获取文档的所有对话"""
        return self.db.get_conversations_by_doc(doc_id)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        references: List[Dict] = None,
        selected_nodes: List[Dict] = None,
        locations: List[Dict] = None
    ) -> Dict[str, Any]:
        """添加消息到对话"""
        return self.db.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            references=references,
            selected_nodes=selected_nodes,
            locations=locations
        )

    def delete_conversation(self, conv_id: str) -> bool:
        """删除对话"""
        return self.db.delete_conversation(conv_id)

    # ============= 库管理 =============

    def create_library(
        self,
        name: str,
        description: str = None,
        color: str = '#4dabf7',
        icon: str = '📁'
    ) -> Dict[str, Any]:
        """创建文档库"""
        return self.db.create_library(name, description, color, icon)

    def get_library(self, lib_id: str) -> Optional[Dict[str, Any]]:
        """获取库详情"""
        return self.db.get_library(lib_id)

    def get_all_libraries(self) -> List[Dict[str, Any]]:
        """获取所有库"""
        return self.db.get_all_libraries()

    def update_library(self, lib_id: str, **kwargs) -> bool:
        """更新库信息"""
        return self.db.update_library(lib_id, **kwargs)

    def delete_library(self, lib_id: str) -> bool:
        """删除库（文档移至未分类）"""
        return self.db.delete_library(lib_id)

    def get_documents_by_library(self, library_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取指定库中的文档"""
        docs = self.db.get_documents_by_library(library_id)
        return [self._format_document(doc) for doc in docs]

    def move_document_to_library(self, doc_id: str, library_id: Optional[str]) -> bool:
        """移动文档到指定库"""
        return self.db.move_document_to_library(doc_id, library_id)

    def get_uncategorized_count(self) -> int:
        """获取未分类文档数量"""
        return self.db.get_uncategorized_count()

    # ============= 统计 =============

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.db.get_stats()

    # ============= 辅助方法 =============

    def _format_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化文档信息"""
        result = {
            'id': doc['id'],
            'name': doc['name'],
            'original_filename': doc.get('original_filename', ''),
            'pdf_path': doc.get('pdf_path', ''),
            'library_id': doc.get('library_id'),
            'status': doc.get('status', 'pending'),
            'stats': {
                'total_nodes': doc.get('total_nodes', 0),
                'max_depth': doc.get('max_depth', 0),
                'total_pages': doc.get('total_pages', 0)
            } if doc.get('total_nodes') else None,
            'file_size': doc.get('file_size', 0),
            'created_at': doc.get('created_at', ''),
            'updated_at': doc.get('updated_at', ''),
            'parsed_at': doc.get('parsed_at', ''),
            'tree_structure': None  # 不在列表中返回完整树结构
        }
        # 如果有错误信息，添加到结果中
        if doc.get('error_message'):
            result['error_message'] = doc['error_message']
        return result
