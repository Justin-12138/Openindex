"""
SQLite3 数据库管理

管理文档库、文档、树结构和对话历史
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class Database:
    """SQLite3 数据库管理器"""

    def __init__(self, db_path: str):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        # 检查并执行迁移
        from .migrations import check_and_migrate
        check_and_migrate(self.db_path)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 文档库表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS libraries (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    color TEXT DEFAULT '#4dabf7',
                    icon TEXT DEFAULT '📁',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 文档表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    original_filename TEXT,
                    pdf_path TEXT,
                    md_path TEXT,
                    tree_path TEXT,
                    mineru_dir TEXT,
                    library_id TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    total_nodes INTEGER DEFAULT 0,
                    max_depth INTEGER DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    file_size INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parsed_at TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE SET NULL
                )
            """)
            
            # 添加 error_message 字段（兼容已存在的数据库）
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN error_message TEXT")
            except sqlite3.OperationalError:
                pass  # 字段已存在
            
            # 添加 library_id 字段（兼容已存在的数据库）
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN library_id TEXT REFERENCES libraries(id) ON DELETE SET NULL")
            except sqlite3.OperationalError:
                pass  # 字段已存在

            # 对话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # 添加 deleted_at 字段（兼容已存在的数据库）
            try:
                cursor.execute("ALTER TABLE conversations ADD COLUMN deleted_at TIMESTAMP")
            except sqlite3.OperationalError:
                pass  # 字段已存在

            # 消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    references_json TEXT,
                    selected_nodes_json TEXT,
                    locations_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)

            # 解析版本表（由迁移脚本创建，这里只创建索引）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_parse_versions_doc 
                ON parse_versions(doc_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_parse_versions_doc_version 
                ON parse_versions(doc_id, version)
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_library ON documents(library_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_doc_id ON conversations(doc_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")

    # ============= 文档管理 =============

    def add_document(
        self,
        doc_id: str,
        name: str,
        original_filename: str,
        pdf_path: str,
        file_size: int = 0
    ) -> Dict[str, Any]:
        """添加文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (id, name, original_filename, pdf_path, file_size, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            """, (doc_id, name, original_filename, pdf_path, file_size))

        return self.get_document(doc_id)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """获取所有文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update_document(self, doc_id: str, **kwargs) -> bool:
        """更新文档"""
        if not kwargs:
            return False

        # 添加更新时间
        kwargs['updated_at'] = datetime.now().isoformat()

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [doc_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE documents SET {fields} WHERE id = ?", values)
            return cursor.rowcount > 0

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        md_path: str = None,
        tree_path: str = None,
        mineru_dir: str = None,
        total_nodes: int = None,
        max_depth: int = None,
        total_pages: int = None,
        error_message: str = None
    ) -> bool:
        """更新文档状态"""
        updates = {'status': status}
        if md_path:
            updates['md_path'] = md_path
        if tree_path:
            updates['tree_path'] = tree_path
        if mineru_dir:
            updates['mineru_dir'] = mineru_dir
        if total_nodes is not None:
            updates['total_nodes'] = total_nodes
        if max_depth is not None:
            updates['max_depth'] = max_depth
        if total_pages is not None:
            updates['total_pages'] = total_pages
        if status == 'ready':
            updates['parsed_at'] = datetime.now().isoformat()
            updates['error_message'] = None  # 清除错误信息
        if status == 'error' and error_message:
            updates['error_message'] = error_message

        return self.update_document(doc_id, **updates)

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            return cursor.rowcount > 0

    def get_documents_by_library(self, library_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取指定库中的文档
        
        Args:
            library_id: 库 ID，None 表示获取未分类的文档
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if library_id:
                cursor.execute(
                    "SELECT * FROM documents WHERE library_id = ? ORDER BY created_at DESC",
                    (library_id,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM documents WHERE library_id IS NULL ORDER BY created_at DESC"
                )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def move_document_to_library(self, doc_id: str, library_id: Optional[str]) -> bool:
        """
        移动文档到指定库
        
        Args:
            doc_id: 文档 ID
            library_id: 目标库 ID，None 表示移至"未分类"
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET library_id = ?, updated_at = ? WHERE id = ?",
                (library_id, datetime.now().isoformat(), doc_id)
            )
            return cursor.rowcount > 0

    # ============= 库管理 =============

    def create_library(
        self,
        name: str,
        description: str = None,
        color: str = '#4dabf7',
        icon: str = '📁'
    ) -> Dict[str, Any]:
        """
        创建文档库
        
        Args:
            name: 库名称
            description: 库描述
            color: 主题色（HEX 格式）
            icon: 图标（emoji）
        """
        lib_id = str(uuid.uuid4())[:8]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO libraries (id, name, description, color, icon)
                VALUES (?, ?, ?, ?, ?)
            """, (lib_id, name, description, color, icon))
        return self.get_library(lib_id)

    def get_library(self, lib_id: str) -> Optional[Dict[str, Any]]:
        """获取库详情"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM libraries WHERE id = ?", (lib_id,))
            row = cursor.fetchone()
            if row:
                lib = self._row_to_dict(row)
                # 获取文档数量
                cursor.execute(
                    "SELECT COUNT(*) FROM documents WHERE library_id = ?",
                    (lib_id,)
                )
                lib['document_count'] = cursor.fetchone()[0]
                return lib
        return None

    def get_all_libraries(self) -> List[Dict[str, Any]]:
        """获取所有库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM libraries ORDER BY name")
            libraries = []
            for row in cursor.fetchall():
                lib = self._row_to_dict(row)
                # 获取文档数量
                cursor.execute(
                    "SELECT COUNT(*) FROM documents WHERE library_id = ?",
                    (lib['id'],)
                )
                lib['document_count'] = cursor.fetchone()[0]
                libraries.append(lib)
            return libraries

    def update_library(self, lib_id: str, **kwargs) -> bool:
        """更新库信息"""
        if not kwargs:
            return False
        
        kwargs['updated_at'] = datetime.now().isoformat()
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [lib_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE libraries SET {fields} WHERE id = ?", values)
            return cursor.rowcount > 0

    def delete_library(self, lib_id: str) -> bool:
        """
        删除库
        
        库中的文档会自动移至"未分类"（library_id 设为 NULL）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM libraries WHERE id = ?", (lib_id,))
            return cursor.rowcount > 0

    def get_uncategorized_count(self) -> int:
        """获取未分类文档数量"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents WHERE library_id IS NULL")
            return cursor.fetchone()[0]

    # ============= 对话管理 =============

    def create_conversation(
        self, 
        doc_id: str, 
        title: str = None,
        first_query: str = None
    ) -> Dict[str, Any]:
        """
        创建对话
        
        Args:
            doc_id: 文档 ID
            title: 对话标题（可选）
            first_query: 第一个查询（可选，用于自动生成标题）
        """
        import uuid
        conv_id = str(uuid.uuid4())[:8]

        if not title:
            if first_query:
                # 使用第一个问题的前 N 个字符作为标题（从配置读取）
                from ..core.config import get_config_value
                max_length = get_config_value('conversation', 'title_max_length', 30)
                if len(first_query) > max_length:
                    title = first_query[:max_length] + "..."
                else:
                    title = first_query
            else:
                title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (id, doc_id, title)
                VALUES (?, ?, ?)
            """, (conv_id, doc_id, title))

        return self.get_conversation(conv_id)

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """获取对话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
            row = cursor.fetchone()
            if row:
                conv = self._row_to_dict(row)
                conv['messages'] = self.get_messages(conv_id)
                return conv
        return None

    def get_conversations_by_doc(
        self, 
        doc_id: str, 
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取文档的所有对话
        
        Args:
            doc_id: 文档 ID
            include_deleted: 是否包含已软删除的对话
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if include_deleted:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE doc_id = ? 
                    ORDER BY updated_at DESC
                """, (doc_id,))
            else:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE doc_id = ? AND deleted_at IS NULL
                    ORDER BY updated_at DESC
                """, (doc_id,))
            conversations = []
            for row in cursor.fetchall():
                conv = self._row_to_dict(row)
                # 获取消息数量
                cursor.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                    (conv['id'],)
                )
                conv['message_count'] = cursor.fetchone()[0]
                conversations.append(conv)
            return conversations

    def update_conversation(self, conv_id: str, title: str = None) -> bool:
        """更新对话"""
        updates = {'updated_at': datetime.now().isoformat()}
        if title:
            updates['title'] = title

        fields = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [conv_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE conversations SET {fields} WHERE id = ?", values)
            return cursor.rowcount > 0

    def delete_conversation(self, conv_id: str, hard: bool = False) -> bool:
        """
        删除对话
        
        Args:
            conv_id: 对话 ID
            hard: 是否硬删除。False 表示软删除（设置 deleted_at），True 表示硬删除
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if hard:
                # 硬删除
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            else:
                # 软删除
                cursor.execute(
                    "UPDATE conversations SET deleted_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), conv_id)
                )
            return cursor.rowcount > 0

    def restore_conversation(self, conv_id: str) -> bool:
        """恢复已软删除的对话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE conversations SET deleted_at = NULL WHERE id = ?",
                (conv_id,)
            )
            return cursor.rowcount > 0

    # ============= 消息管理 =============

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        references: List[Dict] = None,
        selected_nodes: List[Dict] = None,
        locations: List[Dict] = None
    ) -> Dict[str, Any]:
        """添加消息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages 
                (conversation_id, role, content, references_json, selected_nodes_json, locations_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                role,
                content,
                json.dumps(references) if references else None,
                json.dumps(selected_nodes) if selected_nodes else None,
                json.dumps(locations) if locations else None
            ))

            # 更新对话的更新时间
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), conversation_id)
            )

            return {
                'id': cursor.lastrowid,
                'conversation_id': conversation_id,
                'role': role,
                'content': content,
                'references': references,
                'selected_nodes': selected_nodes,
                'locations': locations
            }

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的所有消息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY created_at ASC
            """, (conversation_id,))

            messages = []
            for row in cursor.fetchall():
                msg = self._row_to_dict(row)
                # 解析 JSON 字段
                if msg.get('references_json'):
                    msg['references'] = json.loads(msg['references_json'])
                if msg.get('selected_nodes_json'):
                    msg['selected_nodes'] = json.loads(msg['selected_nodes_json'])
                if msg.get('locations_json'):
                    msg['locations'] = json.loads(msg['locations_json'])
                messages.append(msg)
            return messages

    # ============= 统计 =============

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 文档统计
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'ready'")
            ready_docs = cursor.fetchone()[0]

            # 对话统计
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]

            # 消息统计
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]

            return {
                'total_documents': total_docs,
                'ready_documents': ready_docs,
                'total_conversations': total_conversations,
                'total_messages': total_messages
            }

    # ============= 解析版本管理 =============

    def create_parse_version(
        self,
        doc_id: str,
        version: int = None,
        tree_path: str = None,
        mineru_dir: str = None,
        status: str = 'pending',
        total_nodes: int = 0,
        max_depth: int = 0
    ) -> Dict[str, Any]:
        """
        创建新的解析版本
        
        Args:
            doc_id: 文档 ID
            version: 版本号（如果为 None，则自动递增）
            tree_path: 树结构文件路径
            mineru_dir: MinerU 输出目录
            status: 状态
            total_nodes: 总节点数
            max_depth: 最大深度
            
        Returns:
            版本信息字典
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 如果没有指定版本，获取下一个版本号
            if version is None:
                cursor.execute("""
                    SELECT MAX(version) FROM parse_versions WHERE doc_id = ?
                """, (doc_id,))
                row = cursor.fetchone()
                version = (row[0] or 0) + 1
            
            # 插入新版本
            cursor.execute("""
                INSERT INTO parse_versions 
                (doc_id, version, tree_path, mineru_dir, status, total_nodes, max_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, version, tree_path, mineru_dir, status, total_nodes, max_depth))
            
            # 获取创建的版本
            cursor.execute("""
                SELECT * FROM parse_versions 
                WHERE doc_id = ? AND version = ?
            """, (doc_id, version))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_parse_version(
        self,
        doc_id: str,
        version: int,
        tree_path: str = None,
        mineru_dir: str = None,
        status: str = None,
        error_message: str = None,
        total_nodes: int = None,
        max_depth: int = None
    ) -> bool:
        """
        更新解析版本
        
        Args:
            doc_id: 文档 ID
            version: 版本号
            tree_path: 树结构文件路径
            mineru_dir: MinerU 输出目录
            status: 状态
            error_message: 错误消息
            total_nodes: 总节点数
            max_depth: 最大深度
            
        Returns:
            是否更新成功
        """
        updates = []
        params = []
        
        if tree_path is not None:
            updates.append("tree_path = ?")
            params.append(tree_path)
        if mineru_dir is not None:
            updates.append("mineru_dir = ?")
            params.append(mineru_dir)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if total_nodes is not None:
            updates.append("total_nodes = ?")
            params.append(total_nodes)
        if max_depth is not None:
            updates.append("max_depth = ?")
            params.append(max_depth)
        if status == 'ready':
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if not updates:
            return False
        
        params.extend([doc_id, version])
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE parse_versions 
                SET {', '.join(updates)}
                WHERE doc_id = ? AND version = ?
            """, params)
            return cursor.rowcount > 0

    def get_parse_version(self, doc_id: str, version: int = None) -> Optional[Dict[str, Any]]:
        """
        获取解析版本
        
        Args:
            doc_id: 文档 ID
            version: 版本号（如果为 None，则获取最新版本）
            
        Returns:
            版本信息字典
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if version is None:
                # 获取最新版本
                cursor.execute("""
                    SELECT * FROM parse_versions 
                    WHERE doc_id = ? 
                    ORDER BY version DESC 
                    LIMIT 1
                """, (doc_id,))
            else:
                cursor.execute("""
                    SELECT * FROM parse_versions 
                    WHERE doc_id = ? AND version = ?
                """, (doc_id, version))
            
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_parse_versions(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        获取文档的所有解析版本
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            版本列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM parse_versions 
                WHERE doc_id = ? 
                ORDER BY version DESC
            """, (doc_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_parse_version(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最新解析版本
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            最新版本信息字典
        """
        return self.get_parse_version(doc_id, version=None)

    # ============= 辅助方法 =============

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return dict(row)


# 使用线程本地存储来支持多实例（用于测试和并发场景）
import threading
_local = threading.local()


def get_database(data_dir: str = None) -> Database:
    """
    获取数据库实例
    
    使用线程本地存储，每个线程/协程可以有自己的数据库实例。
    这允许在测试中使用独立的测试数据库，同时在生产环境中
    每个请求可以使用相同的数据库实例。
    
    Args:
        data_dir: 数据目录路径，如果为 None 则使用默认路径
        
    Returns:
        Database 实例
    """
    if not hasattr(_local, 'db_instance') or _local.db_data_dir != data_dir:
        if data_dir is None:
            data_dir = str(Path(__file__).parent / "data")
        db_path = Path(data_dir) / "openindex.db"
        _local.db_instance = Database(str(db_path))
        _local.db_data_dir = data_dir
    return _local.db_instance
