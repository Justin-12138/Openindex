"""
工具函数

提供各种实用工具函数。
"""

import re
import hashlib
from typing import Optional
from pathlib import Path


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    清理字符串，移除不安全字符
    
    Args:
        text: 原始字符串
        max_length: 最大长度（可选）
        
    Returns:
        清理后的字符串
    """
    if not text:
        return ""
    
    # 移除控制字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 移除前后空白
    text = text.strip()
    
    # 限制长度
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_doc_id(doc_id: str) -> bool:
    """
    验证文档ID格式
    
    Args:
        doc_id: 文档ID
        
    Returns:
        是否有效
    """
    if not doc_id:
        return False
    
    # 文档ID应该是8位十六进制字符串
    return bool(re.match(r'^[a-f0-9]{8}$', doc_id.lower()))


def validate_uuid(uuid_str: str) -> bool:
    """
    验证UUID格式
    
    Args:
        uuid_str: UUID字符串
        
    Returns:
        是否有效
    """
    if not uuid_str:
        return False
    
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_str))


def validate_library_id(lib_id: str) -> bool:
    """
    验证库ID格式
    
    Args:
        lib_id: 库ID
        
    Returns:
        是否有效
    """
    if not lib_id:
        return False
    
    # 库ID应该是UUID格式或"uncategorized"
    if lib_id == "uncategorized":
        return True
    
    return validate_uuid(lib_id)


def validate_conversation_id(conv_id: str) -> bool:
    """
    验证对话ID格式
    
    Args:
        conv_id: 对话ID
        
    Returns:
        是否有效
    """
    if not conv_id:
        return False
    
    # 对话ID应该是UUID格式
    return validate_uuid(conv_id)


def calculate_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法（sha256, md5等）
        
    Returns:
        哈希值（十六进制字符串）
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的字符串（如 "1.5 MB"）
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀（当文本被截断时添加）
        
    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
        
    Returns:
        安全的文件名
    """
    if not filename:
        return "unnamed"
    
    # 移除路径分隔符
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # 移除不安全字符
    filename = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', filename)
    
    # 移除连续的下划线
    filename = re.sub(r'_+', '_', filename)
    
    # 移除首尾的下划线和点
    filename = filename.strip('_.')
    
    # 限制长度
    if len(filename) > max_length:
        # 保留扩展名
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            max_name_length = max_length - len(ext) - 1
            filename = name[:max_name_length] + '.' + ext
        else:
            filename = filename[:max_length]
    
    return filename or "unnamed"
