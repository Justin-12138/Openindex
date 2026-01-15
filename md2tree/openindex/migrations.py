"""
数据库迁移脚本

管理数据库 schema 版本和迁移。
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 数据库版本
CURRENT_VERSION = 2


def get_db_version(db_path: Path) -> int:
    """
    获取数据库当前版本
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据库版本号，如果不存在则返回 0
    """
    if not db_path.exists():
        return 0
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            # 检查版本表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            if not cursor.fetchone():
                return 0
            
            # 获取版本
            cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Failed to get database version: {e}")
        return 0


def set_db_version(db_path: Path, version: int) -> None:
    """
    设置数据库版本
    
    Args:
        db_path: 数据库文件路径
        version: 版本号
    """
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # 创建版本表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        
        # 插入新版本记录
        cursor.execute("""
            INSERT INTO schema_version (version, description)
            VALUES (?, ?)
        """, (version, f"Migrated to version {version}"))
        conn.commit()


def migrate_v0_to_v1(db_path: Path) -> None:
    """
    从版本 0 迁移到版本 1
    
    添加必要的字段和索引。
    """
    logger.info("Migrating database from version 0 to version 1...")
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # 检查并添加 error_message 字段
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN error_message TEXT")
            logger.info("Added error_message column to documents table")
        except sqlite3.OperationalError:
            pass  # 字段已存在
        
        # 检查并添加 library_id 字段
        try:
            cursor.execute("""
                ALTER TABLE documents 
                ADD COLUMN library_id TEXT REFERENCES libraries(id) ON DELETE SET NULL
            """)
            logger.info("Added library_id column to documents table")
        except sqlite3.OperationalError:
            pass  # 字段已存在
        
        # 检查并添加 deleted_at 字段到 conversations
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN deleted_at TIMESTAMP")
            logger.info("Added deleted_at column to conversations table")
        except sqlite3.OperationalError:
            pass  # 字段已存在
        
        conn.commit()
        logger.info("Migration to version 1 completed")


def migrate_v1_to_v2(db_path: Path) -> None:
    """
    从版本 1 迁移到版本 2
    
    添加解析版本管理表。
    """
    logger.info("Migrating database from version 1 to version 2...")
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # 创建解析版本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parse_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                tree_path TEXT,
                mineru_dir TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'parsing_mineru', 'parsing_markdown', 
                                  'adding_locations', 'ready', 'error')),
                error_message TEXT,
                total_nodes INTEGER DEFAULT 0,
                max_depth INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(doc_id, version)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parse_versions_doc 
            ON parse_versions(doc_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parse_versions_doc_version 
            ON parse_versions(doc_id, version)
        """)
        
        # 将现有文档的解析结果迁移到版本表（如果 documents 表存在）
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='documents'
            """)
            if cursor.fetchone():
                cursor.execute("""
                    SELECT id, tree_path, mineru_dir, status, total_nodes, max_depth, parsed_at
                    FROM documents
                    WHERE status = 'ready' AND tree_path IS NOT NULL
                """)
                
                existing_docs = cursor.fetchall()
                for doc in existing_docs:
                    doc_id, tree_path, mineru_dir, status, total_nodes, max_depth, parsed_at = doc
                    cursor.execute("""
                        INSERT INTO parse_versions 
                        (doc_id, version, tree_path, mineru_dir, status, total_nodes, max_depth, completed_at)
                        VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                    """, (doc_id, tree_path, mineru_dir, status, total_nodes or 0, max_depth or 0, parsed_at))
        except Exception as e:
            logger.warning(f"Could not migrate existing documents to parse_versions: {e}")
        
        conn.commit()
        logger.info("Migration to version 2 completed")


def migrate_database(db_path: Path, target_version: int = CURRENT_VERSION) -> None:
    """
    迁移数据库到指定版本
    
    Args:
        db_path: 数据库文件路径
        target_version: 目标版本，默认为当前版本
    """
    current_version = get_db_version(db_path)
    
    if current_version >= target_version:
        logger.info(f"Database is already at version {current_version} (target: {target_version})")
        return
    
    logger.info(f"Migrating database from version {current_version} to {target_version}...")
    
    # 执行迁移
    if current_version < 1:
        migrate_v0_to_v1(db_path)
        set_db_version(db_path, 1)
        current_version = 1
    
    # 迁移到版本 2：添加解析版本管理
    if current_version < 2:
        migrate_v1_to_v2(db_path)
        set_db_version(db_path, 2)
        current_version = 2
    
    logger.info(f"Database migration completed. Current version: {get_db_version(db_path)}")


def check_and_migrate(db_path: Path) -> None:
    """
    检查数据库版本并在需要时执行迁移
    
    Args:
        db_path: 数据库文件路径（可以是 Path 对象或字符串）
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)
    
    current_version = get_db_version(db_path)
    
    if current_version < CURRENT_VERSION:
        logger.info(f"Database version {current_version} is older than current version {CURRENT_VERSION}")
        migrate_database(db_path, CURRENT_VERSION)
    elif current_version > CURRENT_VERSION:
        logger.warning(
            f"Database version {current_version} is newer than code version {CURRENT_VERSION}. "
            "Please update the code."
        )
    else:
        logger.debug(f"Database is at current version {CURRENT_VERSION}")
