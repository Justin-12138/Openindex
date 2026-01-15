"""
pytest 配置和共享 fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator

from md2tree.openindex.database import Database
from md2tree.openindex.document_store import DocumentStore


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """创建临时数据目录"""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_database(temp_data_dir: Path) -> Database:
    """创建测试数据库"""
    db_path = temp_data_dir / "test.db"
    return Database(str(db_path))


@pytest.fixture
def test_document_store(temp_data_dir: Path) -> DocumentStore:
    """创建测试文档存储"""
    return DocumentStore(str(temp_data_dir))
