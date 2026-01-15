"""
数据备份工具

提供数据库和文件的备份功能。
"""

import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

logger = logging.getLogger(__name__)


def backup_database(db_path: Path, backup_dir: Path) -> Path:
    """
    备份 SQLite 数据库
    
    Args:
        db_path: 数据库文件路径
        backup_dir: 备份目录
        
    Returns:
        备份文件路径
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成备份文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"openindex_{timestamp}.db"
    backup_path = backup_dir / backup_filename
    
    try:
        # 使用 SQLite 的备份 API（更安全）
        source_conn = sqlite3.connect(str(db_path))
        backup_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        # 如果备份失败，尝试简单的文件复制
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up using file copy to {backup_path}")
            return backup_path
        except Exception as e2:
            logger.error(f"File copy backup also failed: {e2}")
            raise


def backup_files(data_dir: Path, backup_dir: Path) -> Path:
    """
    备份数据文件（PDF、解析结果等）
    
    Args:
        data_dir: 数据目录
        backup_dir: 备份目录
        
    Returns:
        备份目录路径
    """
    if not data_dir.exists():
        logger.warning(f"Data directory not found: {data_dir}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    files_backup_dir = backup_dir / f"files_{timestamp}"
    
    try:
        # 复制整个数据目录
        shutil.copytree(data_dir, files_backup_dir, ignore=shutil.ignore_patterns('*.tmp', '*.log'))
        logger.info(f"Files backed up to {files_backup_dir}")
        return files_backup_dir
    except Exception as e:
        logger.error(f"Failed to backup files: {e}")
        raise


def create_backup(
    db_path: Path,
    data_dir: Path,
    backup_base_dir: Path,
    include_files: bool = True
) -> dict:
    """
    创建完整备份
    
    Args:
        db_path: 数据库文件路径
        data_dir: 数据目录路径
        backup_base_dir: 备份基础目录
        include_files: 是否包含文件备份
        
    Returns:
        备份信息字典
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = backup_base_dir / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_info = {
        "timestamp": timestamp,
        "backup_dir": str(backup_dir),
        "database": None,
        "files": None,
    }
    
    try:
        # 备份数据库
        db_backup_path = backup_database(db_path, backup_dir)
        backup_info["database"] = str(db_backup_path)
        
        # 备份文件（如果启用）
        if include_files:
            files_backup_path = backup_files(data_dir, backup_dir)
            backup_info["files"] = str(files_backup_path)
        
        # 保存备份元信息
        metadata_path = backup_dir / "backup_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Backup completed: {backup_dir}")
        return backup_info
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        # 清理失败的备份目录
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
            except:
                pass
        raise


def list_backups(backup_base_dir: Path) -> list:
    """
    列出所有备份
    
    Args:
        backup_base_dir: 备份基础目录
        
    Returns:
        备份列表（按时间倒序）
    """
    if not backup_base_dir.exists():
        return []
    
    backups = []
    for backup_dir in backup_base_dir.iterdir():
        if not backup_dir.is_dir() or not backup_dir.name.startswith("backup_"):
            continue
        
        metadata_path = backup_dir / "backup_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    backups.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to read backup metadata {metadata_path}: {e}")
    
    # 按时间戳排序（最新的在前）
    backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return backups


def restore_backup(backup_dir: Path, target_db_path: Path, target_data_dir: Path) -> None:
    """
    恢复备份
    
    Args:
        backup_dir: 备份目录
        target_db_path: 目标数据库路径
        target_data_dir: 目标数据目录路径
        
    **警告**: 恢复操作会覆盖现有数据！
    """
    metadata_path = backup_dir / "backup_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Backup metadata not found: {metadata_path}")
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # 恢复数据库
    db_backup_path = Path(metadata.get('database'))
    if db_backup_path and db_backup_path.exists():
        target_db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_backup_path, target_db_path)
        logger.info(f"Database restored from {db_backup_path}")
    
    # 恢复文件
    files_backup_path = metadata.get('files')
    if files_backup_path:
        files_backup = Path(files_backup_path)
        if files_backup.exists():
            if target_data_dir.exists():
                shutil.rmtree(target_data_dir)
            shutil.copytree(files_backup, target_data_dir)
            logger.info(f"Files restored from {files_backup}")
    
    logger.info("Backup restoration completed")


def cleanup_old_backups(backup_base_dir: Path, keep_days: int = 30) -> int:
    """
    清理旧备份
    
    Args:
        backup_base_dir: 备份基础目录
        keep_days: 保留天数
        
    Returns:
        删除的备份数量
    """
    if not backup_base_dir.exists():
        return 0
    
    cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
    deleted_count = 0
    
    for backup_dir in backup_base_dir.iterdir():
        if not backup_dir.is_dir() or not backup_dir.name.startswith("backup_"):
            continue
        
        # 检查备份时间
        try:
            timestamp_str = backup_dir.name.replace("backup_", "")
            backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").timestamp()
            
            if backup_time < cutoff_date:
                shutil.rmtree(backup_dir)
                deleted_count += 1
                logger.info(f"Deleted old backup: {backup_dir}")
        except Exception as e:
            logger.warning(f"Failed to process backup {backup_dir}: {e}")
    
    return deleted_count
